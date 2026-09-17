---
description: "Approve the plan, run implement then diff-review, then halt."
argument-hint: <task-slug>
---
Task slug = "$ARGUMENTS"; the task key (state dir name) is its LAST `/`-segment, so a pasted
branch name like `user/ar-123-title` resolves to `feature-research/ar-123-title/`.
In state.md set plan_verdict=ship, gate=none, iteration += 1.
If iteration > max_iterations, print `■ EXIT · hit max_iterations` and STOP.

REVIEW MODEL: the diff-review gate runs on the model in state.md `review_model:` (`fable` default,
`opus` if the pipeline was started with `--opus`; missing field → treat as `fable`). Read it
fresh; the implementer is unaffected.

REVIEW EFFORT: derived from state.md `tier`, never from a flag.
RE-TIER FIRST — before reading the effort, re-tier against the ACTUAL diff and take the MAX (tier
only ever escalates, never drops). `git diff --stat` showing ≥150 lines OR ≥8 files → at least
HARD; a diff touching security, auth, memory/resource management, concurrency, or
OS/filesystem/process boundaries → at least HARD. Write the resulting `tier:` back to state.md.
Then read the effort off it:
  | tier     | DIFF_REVIEW effort |
  | trivial  | medium             |
  | normal   | medium             |
  | hard     | high               |
  | critical | xhigh              |
Missing or `pending` tier (a pipeline started before tiering existed) → treat as `hard`. Never
`max`, never `low`. Pass the resolved value as the per-invocation effort override and print it as
`<review_effort>` in the banner.

TIER LINE: a re-tier that does not show up in the plan is a silent price change. After writing
`tier:` back to state.md, rewrite the `**Tier:**` line under the plan.md H1 to:
  `**Tier:** <TIER> — implement sonnet/medium · diff_review <review_model>/<review_effort>`
and note the escalation inline when the tier changed (`was <old>: <one-line why>`).

BANNER RULE: finish setup and state.md edits, then print the banner as the last line before
the agent call. Both stages get one — IMPLEMENT before the implementer, DIFF_REVIEW before
the reviewer.

SEQUENCING: stages are sequential because each reads the previous stage's file output
(the reviewer reads the diff + audit.md the implementer just wrote). Invoke one subagent
per message, as its last line, and wait for it to finish — two Agent calls in one message
run in parallel and the reviewer judges files that don't exist yet.

1. Set stage=implement, then (BANNER RULE) print this IMPLEMENT banner as the LAST line before invoking the implementer:
   ```
     ╭─ ⌐■-■  IMPLEMENT · 4/5 · NEO · sonnet/medium
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (24): "Make it small enough to be wrong cheaply." / "Ship the truth, not the hope." / "One reviewable step beats ten clever ones." / "Prove it, then trust it." / "Code is read far more than it is run; write for the reader." / "The first version should be obvious, not impressive." / "Touch only what the plan told you to touch." / "A clever line today is a confused colleague tomorrow." / "Build the boring thing well before the interesting thing at all." / "Done is a diff someone else can understand." / "I know kung fu." / "There is no spoon." / "Don't think you are; know you are." / "There is a difference between knowing the path and walking the path." / "Stop trying to hit me and hit me." / "Guns. Lots of guns." / "I didn't say it would be easy; I just said it would be the truth." / "Free your mind." / "He is beginning to believe." / "That's why it's going to work." / "Change the diff, not the mandate." / "Small enough to revert is small enough to trust." / "Touch what the plan named; leave the rest asleep." / "Stop trying to be clever and be correct."
   Then invoke the **implementer** subagent: execute plan.md; on
   a rework loop fix only "Still open". Writes audit.md. Set stage=diff_review.
1b. TESTS RED? — the implementer gets ONE try at a failing test, then TRINITY takes it.
   After the implementer returns, run the repo's test command. GREEN → step 2. RED → set
   `stage: repair`, `repair_round:` += 1 (abort to you at `repair_round > 2`, reason
   `repair-budget`), and (BANNER RULE) print this REPAIR banner as the LAST line before invoking
   the test-fixer:
   ```
     ╭─ ⌐■-■  REPAIR · 4b/5 · TRINITY · opus/high
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (14): "A red test is a witness — interrogate it, never silence it." / "Dodge this." / "The failing line is the symptom; find the organ." / "Name the cause in one line, or you have not found it." / "A test bent until it passes is a bug with paperwork." / "Flakes do not get fixed; they get named." / "Fix the function every caller shares, not the caller that complained." / "Two reds traded is not one red solved." / "Nobody has ever done this before — that is why it is going to work." / "Green earned by deletion is red in disguise." / "The suite is the one witness that cannot be charmed." / "Patch the cause; the symptom was never the enemy." / "If the approach cannot pass, say so — do not keep patching." / "One try, then the specialist. Flailing is not debugging."
   Then invoke the **test-fixer** subagent (ALWAYS opus/high — `review_model` and `--opus` do not
   apply to it), seeded with the failing test name(s), the command, its output, and the plan's
   "Files touched" list. It writes `feature-research/<task>/repair.md` and sets `repair_verdict:`.
   Route on that verdict: `fixed` → re-run the full suite; green → step 2, still red → another
   repair round. `flake` → note it and go to step 2. `replan` or `needs-human` → print the
   fixer's report and STOP for you (the approach, not the code, is the problem).
2. (BANNER RULE) Print this DIFF-REVIEW banner as the LAST line before invoking the reviewer (substitute `<review_model>` with the state.md value):
   ```
     ╭─ ⌐■-■  DIFF_REVIEW · 5/5 · AGENT SMITH · <review_model>/<review_effort>
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (24): "Your green tests are a comfort, not a verdict." / "The bug you cannot find is the one you decided was not there." / "Untested is unknown, and unknown is unsafe." / "Every assumption is a door you left unlocked." / "Read the diff as if your worst enemy wrote it." / "A passing test proves the test ran, not that the code is right." / "The edge case you skip is the one production will find for you." / "Approve nothing you would not be paged for at midnight." / "Find the failure before the failure finds the user." / "Doubt is the only honest first reaction to working code." / "Mr. Anderson." / "That is the sound of inevitability." / "Never send a human to do a machine's job." / "I'm going to enjoy watching you die, Mr. Anderson." / "We're not here because we're free; we're here because we're not free." / "It is purpose that created us, purpose that connects us, purpose that drives us." / "I'd like to share a revelation I've had during my time here." / "Appalling, isn't it?" / "It's the smell — if there is such a thing." / "You are a plague, and I am the cure." / "Green is not innocence; it is an alibi to check." / "The diff you wave through is the page you write at 3 a.m." / "The case you don't open is the one that reopens you." / "Inevitability, Mr. Anderson — the bug you chose not to see."
   Then invoke the **reviewer** subagent (model override = state.md `review_model`, effort = `<review_effort>` per REVIEW EFFORT) → appends diff review under `## 🔭 Review` in plan.md; sets diff_verdict.
3. Print the GATE 2 TL;DR card and STOP. Fill EVERY value for real (slug, verdict, criteria
   counts from the diff review's `criteria:` line — copy-pasteable, no literal `<task>`); when
   criteria failed, list each on its own indented line with the reviewer's one-line why:
   ```
   ﾊﾐﾐ 0ｺ1  🔴 G A T E  2 · AWAITING YOU  1ｺ0 ﾐﾐﾊ
     ⌐■-■  criteria <proven>/<N> proven<, failed: #<n> <one-line why> — or " (all)">
           tier <TIER><, was <old> — or ""> · reviewed by <review_model>/<review_effort>
           verdict <diff_verdict> → read the diff + plan.md ## 🔭 Review, then
           /anderson:approve-diff <task> to ship, or /anderson:rework <task>.
   ```
   Halt is unconditional even on a ship verdict.
