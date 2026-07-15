---
description: "Loop the implementer on the checker's blocking findings, then diff-review and halt."
argument-hint: <task-slug>
---
Task slug = "$ARGUMENTS". Blocking findings are already in state.md "Still open".
Run exactly the implement → diff_review → halt sequence from approve-plan,
incrementing iteration and stopping if it exceeds max_iterations.

REVIEW MODEL: the diff-review gate runs on the model in state.md `review_model:` (`opus` default,
`fable` if the pipeline was started with `--fable`; missing field → treat as `opus`). Read it
fresh; the implementer is unaffected.

BANNER RULE: state.md edit FIRST, then each banner as the LAST line before
invoking that stage's agent — nothing between banner and agent line; never skip
a banner.

SEQUENCING RULE: the two stages below are STRICTLY SEQUENTIAL — reviewer
consumes the implementer's file outputs (reads the diff + audit.md just
written). Invoke exactly ONE subagent per message, as the LAST thing in it,
then STOP until it fully finishes. NEVER emit both stage agents in same
message / same tool block — that runs them in PARALLEL and the reviewer judges
a diff and audit.md that don't exist yet. Step 2 begins only after step 1's
implementer has stopped.

1. In state.md set iteration += 1 (if iteration > max_iterations, print `■ EXIT · hit max_iterations` and STOP); set stage=implement, then (BANNER RULE) print this IMPLEMENT banner (choose quote by COUNTING, not feel: N = task slug
   character count (every character, hyphens included); iteration = `iteration:`
   value in state.md (read fresh — already reflects this command's increment);
   quote = 0-based item at index (N + 4 + iteration) mod M; M = integer in
   "Pool (M):" label below; count list from 0; mod M always yields valid
   position (0 to M−1); label number must equal actual item count.
   Do NOT pick "at random", do NOT default to first.) as the LAST line before invoking the implementer:
   ```
     ╭─ ⌐■-■  IMPLEMENT · 4/5 · NEO · sonnet/medium
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (24): "Make it small enough to be wrong cheaply." / "Ship the truth, not the hope." / "One reviewable step beats ten clever ones." / "Prove it, then trust it." / "Code is read far more than it is run; write for the reader." / "The first version should be obvious, not impressive." / "Touch only what the plan told you to touch." / "A clever line today is a confused colleague tomorrow." / "Build the boring thing well before the interesting thing at all." / "Done is a diff someone else can understand." / "I know kung fu." / "There is no spoon." / "Don't think you are; know you are." / "There is a difference between knowing the path and walking the path." / "Stop trying to hit me and hit me." / "Guns. Lots of guns." / "I didn't say it would be easy; I just said it would be the truth." / "Free your mind." / "He is beginning to believe." / "That's why it's going to work." / "Change the diff, not the mandate." / "Small enough to revert is small enough to trust." / "Touch what the plan named; leave the rest asleep." / "Stop trying to be clever and be correct."
   Then invoke the implementer subagent: fix only "Still open". Writes audit.md.
   Set stage=diff_review.
2. (BANNER RULE) Print this DIFF-REVIEW banner (choose quote by COUNTING, not feel: N = task slug
   character count (every character, hyphens included); iteration = `iteration:`
   value in state.md (read fresh — already reflects this command's increment);
   quote = 0-based item at index (N + 5 + iteration) mod M; M = integer in
   "Pool (M):" label below; count list from 0; mod M always yields valid
   position (0 to M−1); label number must equal actual item count.
   Do NOT pick "at random", do NOT default to first.) as the LAST line before invoking the reviewer (substitute `<review_model>` with the state.md value):
   ```
     ╭─ ⌐■-■  DIFF_REVIEW · 5/5 · AGENT SMITH · <review_model>/xhigh
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (24): "Your green tests are a comfort, not a verdict." / "The bug you cannot find is the one you decided was not there." / "Untested is unknown, and unknown is unsafe." / "Every assumption is a door you left unlocked." / "Read the diff as if your worst enemy wrote it." / "A passing test proves the test ran, not that the code is right." / "The edge case you skip is the one production will find for you." / "Approve nothing you would not be paged for at midnight." / "Find the failure before the failure finds the user." / "Doubt is the only honest first reaction to working code." / "Mr. Anderson." / "That is the sound of inevitability." / "Never send a human to do a machine's job." / "I'm going to enjoy watching you die, Mr. Anderson." / "We're not here because we're free; we're here because we're not free." / "It is purpose that created us, purpose that connects us, purpose that drives us." / "I'd like to share a revelation I've had during my time here." / "Appalling, isn't it?" / "It's the smell — if there is such a thing." / "You are a plague, and I am the cure." / "Green is not innocence; it is an alibi to check." / "The diff you wave through is the page you write at 3 a.m." / "The case you don't open is the one that reopens you." / "Inevitability, Mr. Anderson — the bug you chose not to see."
   Then invoke the reviewer subagent (model override = state.md `review_model`, effort xhigh) → appends diff review under `## 🔭 Review` in plan.md; sets diff_verdict.
3. Print the GATE 2 line exactly as approve-plan.md step 3 does, then STOP.
