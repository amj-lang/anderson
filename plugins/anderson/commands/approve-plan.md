---
description: "Approve the plan, run implement then diff-review, then halt."
argument-hint: <task-slug>
---
Task slug = "$ARGUMENTS". In state.md set plan_verdict=ship, gate=none, iteration += 1.
If iteration > max_iterations, print `■ EXIT · hit max_iterations` and STOP.

BANNER RULE: for each stage below, do the state.md edit FIRST, then print the
banner as the LAST line before invoking that stage's agent — nothing between the
banner and the agent line; never skip a banner.

1. Set stage=implement, then (BANNER RULE) print this IMPLEMENT banner (choose the quote by COUNTING, not by feel: let N = the number of characters in the task slug (just its length — count every character, including hyphens); let iteration = the `iteration:` value currently in state.md (read it fresh — at this step it already reflects this command's increment); the quote is the 0-based item at index (N + 4 + iteration) mod 10 in the Pool below — count the list from 0; the Pool has exactly 10 items so mod 10 always yields a valid position (0–9). Do NOT pick "at random" and do NOT default to the first.) as the LAST line before invoking the implementer:
   ```
     ╭─ ⌐■-■  IMPLEMENT · 4/5 · NEO · sonnet/medium
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (10): "Make it small enough to be wrong cheaply." / "Ship the truth, not the hope." / "One reviewable step beats ten clever ones." / "Prove it, then trust it." / "Code is read far more than it is run; write for the reader." / "The first version should be obvious, not impressive." / "Touch only what the plan told you to touch." / "A clever line today is a confused colleague tomorrow." / "Build the boring thing well before the interesting thing at all." / "Done is a diff someone else can understand."
   Then invoke the **implementer** subagent: execute plan.md; on
   a rework loop fix only "Still open". Writes audit.md. Set stage=diff_review.
2. (BANNER RULE) Print this DIFF-REVIEW banner (choose the quote by COUNTING, not by feel: let N = the number of characters in the task slug (just its length — count every character, including hyphens); let iteration = the `iteration:` value currently in state.md (read it fresh — at this step it already reflects this command's increment); the quote is the 0-based item at index (N + 5 + iteration) mod 10 in the Pool below — count the list from 0; the Pool has exactly 10 items so mod 10 always yields a valid position (0–9). Do NOT pick "at random" and do NOT default to the first.) as the LAST line before invoking the reviewer:
   ```
     ╭─ ⌐■-■  DIFF_REVIEW · 5/5 · AGENT SMITH · opus/xhigh
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (10): "Your green tests are a comfort, not a verdict." / "The bug you cannot find is the one you decided was not there." / "Untested is unknown, and unknown is unsafe." / "Every assumption is a door you left unlocked." / "Read the diff as if your worst enemy wrote it." / "A passing test proves the test ran, not that the code is right." / "The edge case you skip is the one production will find for you." / "Approve nothing you would not be paged for at midnight." / "Find the failure before the failure finds the user." / "Doubt is the only honest first reaction to working code."
   Then invoke the **reviewer** subagent → writes diff-review.md, sets diff_verdict.
3. Print and STOP — fill in the real task slug for every `<task>` and the real
   verdict for `<diff_verdict>` so the commands + path are copy-pasteable (e.g.
   `/anderson:approve-diff brief-views`, NOT a literal `<task>`):
   `■ GATE 2 · awaiting you. Read feature-research/<task>/diff-review.md AND the actual diff (verdict=<diff_verdict>). Then /anderson:approve-diff <task> to ship, or /anderson:rework <task>.`
   Halt is unconditional even on a ship verdict.
