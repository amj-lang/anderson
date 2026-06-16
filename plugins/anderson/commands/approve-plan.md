---
description: "Approve the plan, run implement then diff-review, then halt."
argument-hint: <task-slug>
---
Task slug = "$ARGUMENTS". In state.md set plan_verdict=ship, gate=none, iteration += 1.
If iteration > max_iterations, print `■ EXIT · hit max_iterations` and STOP.

1. Print this IMPLEMENT banner (pick ONE quote at random — never default to the first, and don't reuse one you showed earlier this session):
   ```
     ✦ ⌐■-■  A N D E R S O N  ✦   ·   3/4 · IMPLEMENT
           NEO · implementer · sonnet · medium · executing plan.md
           "[one quote from the pool]"
   ```
   Pool (10): "Make it small enough to be wrong cheaply." / "Ship the truth, not the hope." / "One reviewable step beats ten clever ones." / "Prove it, then trust it." / "Code is read far more than it is run; write for the reader." / "The first version should be obvious, not impressive." / "Touch only what the plan told you to touch." / "A clever line today is a confused colleague tomorrow." / "Build the boring thing well before the interesting thing at all." / "Done is a diff someone else can understand."
   Set stage=implement. Invoke the **implementer** subagent: execute plan.md; on
   a rework loop fix only "Still open". Writes audit.md. Set stage=diff_review.
2. Print this DIFF-REVIEW banner (pick ONE quote at random — never default to the first, and don't reuse one you showed earlier this session):
   ```
     ✦ ⌐■-■  A N D E R S O N  ✦   ·   4/4 · DIFF_REVIEW
           AGENT SMITH · reviewer · opus · xhigh · read-only diff review
           "[one quote from the pool]"
   ```
   Pool (10): "Your green tests are a comfort, not a verdict." / "The bug you cannot find is the one you decided was not there." / "Untested is unknown, and unknown is unsafe." / "Every assumption is a door you left unlocked." / "Read the diff as if your worst enemy wrote it." / "A passing test proves the test ran, not that the code is right." / "The edge case you skip is the one production will find for you." / "Approve nothing you would not be paged for at midnight." / "Find the failure before the failure finds the user." / "Doubt is the only honest first reaction to working code."
   Invoke the **reviewer** subagent → writes diff-review.md, sets diff_verdict.
3. Print and STOP — fill in the real task slug for every `<task>` and the real
   verdict for `<diff_verdict>` so the commands + path are copy-pasteable (e.g.
   `/anderson:approve-diff brief-views`, NOT a literal `<task>`):
   `■ GATE 2 · awaiting you. Read feature-research/<task>/diff-review.md AND the actual diff (verdict=<diff_verdict>). Then /anderson:approve-diff <task> to ship, or /anderson:rework <task>.`
   Halt is unconditional even on a ship verdict.
