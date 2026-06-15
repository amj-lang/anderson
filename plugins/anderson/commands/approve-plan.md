---
description: "Approve the plan, run implement then diff-review, then halt."
argument-hint: <task-slug>
---
Task slug = "$ARGUMENTS". In state.md set plan_verdict=ship, gate=none, iteration += 1.
If iteration > max_iterations, print `■ EXIT · hit max_iterations` and STOP.

1. Print this IMPLEMENT banner (pick one quote):
   ```
     ⌐■-■  A N D E R S O N   ·   3/4 · IMPLEMENT
           NEO · implementer · sonnet · medium · executing plan.md
           "[one quote from the pool]"
   ```
   Pool: "Make it small enough to be wrong cheaply." / "Ship the truth, not the hope." / "One reviewable step beats ten clever ones." / "Prove it, then trust it."
   Set stage=implement. Invoke the **implementer** subagent: execute plan.md; on
   a rework loop fix only "Still open". Writes audit.md. Set stage=diff_review.
2. Print this DIFF-REVIEW banner (pick one quote):
   ```
     ⌐■-■  A N D E R S O N   ·   4/4 · DIFF_REVIEW
           AGENT SMITH · reviewer · opus · xhigh · read-only diff review
           "[one quote from the pool]"
   ```
   Pool: "Your green tests are a comfort, not a verdict." / "The bug you cannot find is the one you decided was not there." / "Untested is unknown, and unknown is unsafe." / "Every assumption is a door you left unlocked."
   Invoke the **reviewer** subagent → writes diff-review.md, sets diff_verdict.
3. Print and STOP:
   `■ GATE 2 · awaiting you. Read feature-research/<task>/diff-review.md AND the actual diff (verdict=<diff_verdict>). Then /anderson:approve-diff <task> to ship, or /anderson:rework <task>.`
   Halt is unconditional even on a ship verdict.
