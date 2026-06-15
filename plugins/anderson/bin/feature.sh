#!/usr/bin/env bash
# feature.sh — headless driver for the anderson pipeline (CI / walk-away runs).
# Deterministic gating: runs each chain with the right model and EXITS at a human
# gate; resume by re-running with the matching flag. Interactive users can use the
# /anderson:* slash commands instead. Requires the anderson plugin installed and the
# `claude` CLI on PATH. Run from your repo root.
#
#   ./feature.sh start <task> "<goal>"      # plan -> plan_review, halt
#   ./feature.sh --approve-plan <task>      # implement -> diff_review, halt
#   ./feature.sh --approve-diff <task>      # ship
#   ./feature.sh --rework <task>            # loop implement on checker findings
set -euo pipefail
ROOT="feature-research"; task="${2:-}"; dir="$ROOT/$task"; state="$dir/state.md"

seed_state() {
  mkdir -p "$dir"
  grep -qE '^[[:space:]]*/?feature-research/?[[:space:]]*$' .gitignore 2>/dev/null || echo "feature-research/" >> .gitignore
  cat > "$state" << TPL
# Pipeline state
<!-- STATE:START -->
task:            $task
stage:           plan
gate:            none
iteration:       0
max_iterations:  2
exit_rule:       all tests pass and lint clean, only major issues fixed
plan_verdict:    pending
diff_verdict:    pending
<!-- STATE:END -->

## Done so far

## Still open
TPL
}
get() { grep -E "^$1:" "$state" | head -1 | sed -E "s/^$1:[[:space:]]*//; s/[[:space:]]*#.*//" || true; }
set_field() { sed -i.bak -E "s|^($1:[[:space:]]*).*|\1$2|" "$state" && rm -f "$state.bak"; }
run() { claude -p "$3" --model "$1" --permission-mode "$2" --output-format json | tee -a "$dir/run.log"; }

plan()        { run opus   acceptEdits "Use the planner subagent on task '$task'. Goal: $goal. Write feature-research/$task/plan.md."; set_field stage plan_review; }
plan_review() { run opus   acceptEdits "Use the plan-reviewer subagent on task '$task'. stage=plan_review. Edit plan.md in place, prepend '## Diverged because', keep plan.orig.md, set plan_verdict."
                set_field gate human
                echo ">>> PLAN GATE. Read $dir/plan.md ('## Diverged because', verdict $(get plan_verdict)); original at plan.orig.md."
                echo ">>> Approve: ./feature.sh --approve-plan $task"; exit 10; }
implement()   { it=$(( $(get iteration) + 1 )); set_field iteration "$it"
                [ "$it" -gt "$(get max_iterations)" ] && { echo ">>> EXIT: hit max_iterations. Escalating to you."; exit 1; }
                set_field stage implement; set_field gate none
                run sonnet acceptEdits "Use the implementer subagent on task '$task'. Execute plan.md (iteration $it); on rework fix only 'Still open'. Write audit.md."
                set_field stage diff_review; }
diff_review() { run opus   acceptEdits "Use the reviewer subagent on task '$task'. stage=diff_review. Diff-review the union scope; write diff-review.md; set diff_verdict."
                set_field gate human
                echo ">>> DIFF GATE. Read $dir/diff-review.md (verdict $(get diff_verdict)) AND the diff."
                echo ">>> Ship: ./feature.sh --approve-diff $task | Loop: ./feature.sh --rework $task"; exit 20; }

case "${1:-}" in
  start)         goal="${3:?need a goal}"; seed_state; set_field task "$task"; plan; plan_review;;
  --approve-plan) set_field plan_verdict ship; set_field gate none; implement; diff_review;;
  --approve-diff) set_field diff_verdict ship; set_field stage done; echo ">>> DONE: $task shipped. Suggested commit: \"$task (review: ship)\". Read what merged — green != understood."; rm -rf "$dir";;
  --rework)      implement; diff_review;;
  *) echo "usage: feature.sh start <task> \"<goal>\" | --approve-plan <task> | --approve-diff <task> | --rework <task>"; exit 64;;
esac
