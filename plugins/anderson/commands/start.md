---
description: "Start the gated build loop: plan then plan-review, then halt. Invoke as /anderson:start."
argument-hint: <task-slug> <one-line goal>
allowed-tools: Bash(grep:*), Bash(echo:*)
---
Task slug = first word of "$ARGUMENTS"; goal = the rest.

Print this PLAN banner (pick one quote from the pool, vary it run to run), then act:
```
  ⌐■-■  A N D E R S O N   ·   1/4 · PLAN
        THE ARCHITECT · planner · opus · high · scoping → plan.md
        "[one quote from the pool]"
```
Pool: "Design twice, so reality only has to happen once." / "The most dangerous flaw is the one the blueprint calls a feature." / "What you do not name in the plan will name itself in production." / "Scope is a fire: contain it or feed it."

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
4. Print this PLAN-REVIEW banner (pick one quote):
   ```
     ⌐■-■  A N D E R S O N   ·   2/4 · PLAN_REVIEW
           THE ORACLE · plan-reviewer · opus · xhigh · editing plan.md
           "[one quote from the pool]"
   ```
   Pool: "The flaw hides in the part everyone agreed not to question." / "A question carries more weight than any answer it returns." / "The map is not the territory, and the demo is not the system." / "Ask what it costs before you ask what it does."
   Invoke the **plan-reviewer** subagent → edits plan.md in place, prepends
   "## Diverged because", keeps plan.orig.md, sets plan_verdict.
5. Print and STOP:
   `■ GATE 1 · your turn. Read feature-research/<task>/plan.md (## Diverged because, verdict=<plan_verdict>). Then /anderson:approve-plan <task> — or just say "approved, go". Don't implement yet.`
   Halt is unconditional even on a ship verdict.
