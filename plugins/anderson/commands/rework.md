---
description: "Loop the implementer on the checker's blocking findings, then diff-review and halt."
argument-hint: <task-slug>
---
Task slug = "$ARGUMENTS". Blocking findings are already in state.md "Still open".
Run exactly the implement → diff_review → halt sequence from approve-plan,
incrementing iteration and stopping if it exceeds max_iterations.

BANNER RULE: do the state.md edit FIRST, then print each banner as the LAST line
before invoking that stage's agent — nothing between the banner and the agent
line; never skip a banner.

1. In state.md set iteration += 1 (if iteration > max_iterations, print `■ EXIT · hit max_iterations` and STOP); set stage=implement, then (BANNER RULE) print this IMPLEMENT banner (choose the quote by COUNTING, not by feel: let N = the number of characters in the
   task slug (just its length — count every character, including hyphens); let iteration
   = the `iteration:` value currently in state.md (read it fresh — at this step it already
   reflects this command's increment); the quote is the 0-based item at index
   (N + 4 + iteration) mod M, where M is the integer printed in the "Pool (M):" label
   below — count the list from 0; mod M always yields a valid position (0 to M−1).
   (M is read from the label, so the label number must always equal the actual item count.)
   Do NOT pick "at random" and do NOT default to the first.) as the LAST line before invoking the implementer:
   ```
     ╭─ ⌐■-■  IMPLEMENT · 4/5 · NEO · sonnet/medium
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (20): "Make it small enough to be wrong cheaply." / "Ship the truth, not the hope." / "One reviewable step beats ten clever ones." / "Prove it, then trust it." / "Code is read far more than it is run; write for the reader." / "The first version should be obvious, not impressive." / "Touch only what the plan told you to touch." / "A clever line today is a confused colleague tomorrow." / "Build the boring thing well before the interesting thing at all." / "Done is a diff someone else can understand." / "I know kung fu." / "There is no spoon." / "Don't think you are; know you are." / "There is a difference between knowing the path and walking the path." / "Stop trying to hit me and hit me." / "Guns. Lots of guns." / "I didn't say it would be easy; I just said it would be the truth." / "Free your mind." / "He is beginning to believe." / "That's why it's going to work."
   Then invoke the implementer subagent: fix only "Still open". Writes audit.md.
   Set stage=diff_review.
2. (BANNER RULE) Print this DIFF-REVIEW banner (choose the quote by COUNTING, not by feel: let N = the number of characters in the
   task slug (just its length — count every character, including hyphens); let iteration
   = the `iteration:` value currently in state.md (read it fresh — at this step it already
   reflects this command's increment); the quote is the 0-based item at index
   (N + 5 + iteration) mod M, where M is the integer printed in the "Pool (M):" label
   below — count the list from 0; mod M always yields a valid position (0 to M−1).
   (M is read from the label, so the label number must always equal the actual item count.)
   Do NOT pick "at random" and do NOT default to the first.) as the LAST line before invoking the reviewer:
   ```
     ╭─ ⌐■-■  DIFF_REVIEW · 5/5 · AGENT SMITH · opus/xhigh
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (20): "Your green tests are a comfort, not a verdict." / "The bug you cannot find is the one you decided was not there." / "Untested is unknown, and unknown is unsafe." / "Every assumption is a door you left unlocked." / "Read the diff as if your worst enemy wrote it." / "A passing test proves the test ran, not that the code is right." / "The edge case you skip is the one production will find for you." / "Approve nothing you would not be paged for at midnight." / "Find the failure before the failure finds the user." / "Doubt is the only honest first reaction to working code." / "Mr. Anderson." / "That is the sound of inevitability." / "Never send a human to do a machine's job." / "I'm going to enjoy watching you die, Mr. Anderson." / "We're not here because we're free; we're here because we're not free." / "It is purpose that created us, purpose that connects us, purpose that drives us." / "I'd like to share a revelation I've had during my time here." / "Appalling, isn't it?" / "It's the smell — if there is such a thing." / "You are a plague, and I am the cure."
   Then invoke the reviewer subagent → appends diff review under `## 🔭 Review` in plan.md; sets diff_verdict.
3. Print the GATE 2 line exactly as approve-plan.md step 3 does, then STOP.
