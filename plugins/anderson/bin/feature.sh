#!/usr/bin/env bash
# feature.sh — headless driver for the anderson pipeline (CI / walk-away runs).
# Deterministic gating: runs each chain with the right model and EXITS at a human
# gate; resume by re-running with the matching flag. Interactive users can use the
# /anderson:* slash commands instead. Requires the anderson plugin installed and the
# `claude` CLI on PATH. Run from your repo root.
#
#   ./feature.sh start <task> "<goal>"      # plan -> plan_review, halt
#   ./feature.sh seed <task> ...            # only write state.md (idempotent); /anderson:start runs it
#                                           # first so the fleet monitor shows the row before the planner
#   ./feature.sh --approve-plan <task>      # implement -> diff_review, halt
#   ./feature.sh --approve-diff <task>      # ship: branch + commit + push + PR (guarded)
#   ./feature.sh --rework <task>            # loop implement on checker findings
# Models are fixed per stage (docs/tiering.md); the review agents size effort from state.md `tier`.
set -euo pipefail
ROOT="feature-research"; slug="${2:-}"
if [ "${1:-}" = "seed" ]; then           # seed <slug> [goal words…]: slug = first non-flag word
  slug=""; for _a in "${@:2}"; do case "$_a" in --*) ;; *) slug="$_a"; break ;; esac; done
fi
# Task key = last `/`-segment: a pasted branch name (Linear: user/ar-123-title) keeps the state
# dir flat, which is what the statusline, scheduler and fleet monitor glob. The full slug, when it
# had a `/`, is recorded as `branch:` and used verbatim at ship time.
task="${slug##*/}"; dir="$ROOT/$task"; state="$dir/state.md"
BRANCH_SEED=""; case "$slug" in */*) BRANCH_SEED="$slug" ;; esac
ORIG_TASK="$task"; ADOPTED=""   # adopt_existing may point task/dir/state at an existing task dir

# Same work, richer slug: `/anderson:start ais-showcase-poses` then, once the ticket turns up,
# `/anderson:start ar-2168-ais-showcase-poses` used to leave two task dirs for one session — and
# fleet, which reads the newest state.md under the repo, then showed both agents on the same task.
# So before seeding a new dir, adopt an existing one whose slug matches modulo a ticket prefix.
adopt_existing() {
  [ -d "$dir" ] && return 0
  local base="${task#*[0-9]-}" n nb
  for d in "$ROOT"/*/; do
    [ -f "$d/state.md" ] || continue
    n="$(basename "$d")"; nb="${n#*[0-9]-}"
    if [ "$n" != "$task" ] && [ "$nb" = "$base" ]; then
      task="$n"; dir="$ROOT/$task"; state="$dir/state.md"
      ADOPTED="$n"
      return 0
    fi
  done
}

seed_state() {
  mkdir -p "$dir"
  grep -qE '^[[:space:]]*/?feature-research/?[[:space:]]*$' .gitignore 2>/dev/null || echo "feature-research/" >> .gitignore
  cat > "$state" << TPL
# Pipeline state
<!-- STATE:START -->
task:            $task
${BRANCH_SEED:+branch:          $BRANCH_SEED
}stage:           plan
gate:            none
iteration:       0
max_iterations:  2
exit_rule:       all tests pass and lint clean, only major issues fixed
tier:            pending
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

_tty=1; [ -t 1 ] || _tty=0; case "${TERM:-}" in dumb|"") _tty=0 ;; esac
_color=1; if [ -n "${NO_COLOR:-}" ] || [ "$_tty" -eq 0 ]; then _color=0; fi
grn(){ if [ "$_color" -eq 1 ]; then printf '\033[32m'; fi; }
red(){ if [ "$_color" -eq 1 ]; then printf '\033[31m'; fi; }
rst(){ if [ "$_color" -eq 1 ]; then printf '\033[0m';  fi; }

plan()        { run opus acceptEdits "Use the planner subagent on task '$task'. Goal: $goal. Write feature-research/$task/plan.md."; set_field stage plan_review; }
plan_review() { run opus acceptEdits "Use the plan-reviewer subagent on task '$task'. stage=plan_review. Make inline strike-through edits in plan.md, append review under ## 🔭 Review, set plan_verdict."
                set_field gate human
                red; printf '>>> PLAN GATE. Read %s/plan.md (## 🔭 Review, verdict %s).\n' "$dir" "$(get plan_verdict)"; rst
                printf '>>> Approve: ./feature.sh --approve-plan %s\n' "$task"; exit 10; }
implement()   { it=$(( $(get iteration) + 1 )); set_field iteration "$it"
                [ "$it" -gt "$(get max_iterations)" ] && { echo ">>> EXIT: hit max_iterations. Escalating to you."; exit 1; }
                set_field stage implement; set_field gate none
                run sonnet acceptEdits "Use the implementer subagent on task '$task'. Execute plan.md (iteration $it); on rework fix only 'Still open'. Write audit.md."
                set_field stage diff_review; }
diff_review() { run opus acceptEdits "Use the reviewer subagent on task '$task'. stage=diff_review. Diff-review the union scope; append diff review under ## 🔭 Review in plan.md; set diff_verdict."
                set_field gate human
                red; printf '>>> DIFF GATE. Read %s/plan.md (## 🔭 Review, verdict %s) AND the diff.\n' "$dir" "$(get diff_verdict)"; rst
                printf '>>> Ship: ./feature.sh --approve-diff %s | Loop: ./feature.sh --rework %s\n' "$task" "$task"; exit 20; }

# ship — fold the diff-review verdict into a real commit + PR, guarded for any repo / CI.
# Builds the message from the scratch BEFORE deleting it, branches off the default branch
# when needed, commits under an identity (sets a CI fallback only if none), and — when a
# remote + gh are present — pushes and opens the PR. Degrades gracefully: no git repo / no
# remote / no gh -> does as much as it safely can and prints the rest. Never force-pushes.
ship() {
  set_field diff_verdict ship; set_field stage done
  local title subj bodyfile current default branch url
  title="$(sed -n 's/^# //p' "$dir/plan.md" 2>/dev/null | head -1 || true)"
  subj="${title:-$task} (review: ship)"
  bodyfile="$(mktemp)"
  {
    echo "${title:-$task}"
    echo
    echo "Shipped by anderson (gated maker/checker loop). Diff-review verdict: ship."
    [ -f "$dir/plan.md" ] && { echo; echo "## Diff review"; echo; sed -n '/^## 🔭 Review/,$p' "$dir/plan.md"; }
    [ -f "$dir/audit.md" ]       && { echo; echo "## Implementation audit"; echo; cat "$dir/audit.md"; }
  } > "$bodyfile"

  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo ">>> Not a git repo — skipped commit/PR. Subject: \"$subj\". PR body: $bodyfile"
    rm -rf "$dir"; return 0
  fi
  [ -z "$(git config user.email || true)" ] && { git config user.email "anderson@ci.local"; git config user.name "anderson"; }

  current="$(git rev-parse --abbrev-ref HEAD)"
  default="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@' || true)"
  [ -z "$default" ] && { git show-ref --verify --quiet refs/heads/main && default=main || { git show-ref --verify --quiet refs/heads/master && default=master || default="$current"; }; }

  branch="$current"
  if [ "$current" = "$default" ] || [ "$current" = "HEAD" ]; then
    branch="$(get branch)"; [ -n "$branch" ] || branch="anderson/$task"
    if git show-ref --verify --quiet "refs/heads/$branch"; then git switch "$branch"; else git switch -c "$branch"; fi
  fi
  echo ">>> Branch: $branch (base: $default)"

  git add -A
  if git diff --cached --quiet; then
    echo ">>> Nothing to commit (already committed?)."
  else
    git commit -m "$subj" -m "$(cat "$bodyfile")"
    echo ">>> Committed: $subj"
  fi

  if [ -n "$(git remote)" ]; then
    git push -u origin "$branch"
    if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
      url="$(gh pr create --base "$default" --head "$branch" --title "$subj" --body-file "$bodyfile" 2>&1 || true)"
      echo ">>> PR: $url"
    else
      echo ">>> Pushed $branch. No gh/auth — open the PR manually (base $default). Body: $bodyfile"
    fi
  else
    echo ">>> No remote — committed locally on $branch. PR body: $bodyfile"
  fi

  rm -rf "$dir"
  echo ">>> DONE: $task shipped on $branch. Read what merged — green != understood."
}

case "${1:-}" in
  seed)          [ -n "$slug" ] || { echo "seed: no task slug given"; exit 64; }
                 adopt_existing
                 if [ -f "$state" ]; then echo "state: $state already there (stage $(get stage))${ADOPTED:+ — ADOPTED for this session, use task key $task, do NOT create $ORIG_TASK}"
                 else seed_state; echo "state: $state seeded (stage plan)${BRANCH_SEED:+, branch $BRANCH_SEED}"; fi;;
  start)         goal="${3:?need a goal}"; adopt_existing; seed_state; set_field task "$task"; plan; plan_review;;
  --approve-plan) set_field plan_verdict ship; set_field gate none; implement; diff_review;;
  --approve-diff) ship;;
  --rework)      implement; diff_review;;
  *) echo "usage: feature.sh start <task> \"<goal>\" | seed <task> | --approve-plan <task> | --approve-diff <task> | --rework <task>"; exit 64;;
esac
