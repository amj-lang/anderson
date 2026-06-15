---
description: "Start the gated build loop: plan then plan-review, then halt. Invoke as /anderson:start."
argument-hint: <task-slug> <one-line goal>
allowed-tools: Bash(grep:*), Bash(echo:*)
---
Task slug = first word of "$ARGUMENTS"; goal = the rest.

Print this banner verbatim, then act:
`▶ [anderson 1/4 · PLAN] agent=planner · model=opus · effort=high · scoping → plan.md`

1. Make sure the scratch dir is ignored by git (it's disposable):
   if `feature-research/` is not already in `.gitignore`, append it.
2. If `feature-research/<task>/state.md` is absent, create it with this EXACT block
   (substitute `<task>` with the task slug). This block is machine-read by
   `hooks/scheduler.py`, `commands/status.md`, and `bin/feature.sh`; the format
   must be byte-faithful — column-0 `key:`, the two STATE comments, no markdown
   bullets or bold:
   ```
   # Pipeline state
   <!-- STATE:START -->
   task:            <task>
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
   ```
3. Invoke the **planner** subagent (goal = rest of $ARGUMENTS) → writes plan.md.
   Set stage=plan_review.
4. Print: `▶ [anderson 2/4 · PLAN-REVIEW] agent=plan-reviewer · model=opus · effort=xhigh · editing plan.md`
   Invoke the **plan-reviewer** subagent → edits plan.md in place, prepends
   "## Diverged because", keeps plan.orig.md, sets plan_verdict.
5. Print and STOP:
   `■ GATE 1 · your turn. Read feature-research/<task>/plan.md (## Diverged because, verdict=<plan_verdict>). Then /anderson:approve-plan <task> — or just say "approved, go". Don't implement yet.`
   Halt is unconditional even on a ship verdict.
