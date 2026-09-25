---
description: "Loop the implementer on the checker's blocking findings, then diff-review and halt."
argument-hint: <task-slug>
---
Task slug = "$ARGUMENTS"; the task key (state dir name) is its LAST `/`-segment, so a pasted
branch name like `user/ar-123-title` resolves to `feature-research/ar-123-title/`.
Blocking findings are already in state.md "Still open".
Run exactly the implement → diff_review → halt sequence from approve-plan,
incrementing iteration and stopping if it exceeds max_iterations. A round that leaves the tests
RED goes to TRINITY (step 1b), never back to the implementer: the implementer gets one try at a
failing test, and looping it on a red suite is the failure mode this stage exists to stop.

REVIEW MODEL: the diff reviewer always runs on opus (agent frontmatter); no flag, no state field.

REVIEW EFFORT: derived from state.md `tier`.
RE-TIER FIRST — before reading the effort, re-tier against the ACTUAL diff and take the MAX (tier
only ever escalates, never drops). `git diff --stat` showing ≥150 lines OR ≥8 files → at least
HARD; a diff touching security, auth, memory/resource management, concurrency, or
OS/filesystem/process boundaries → at least HARD. Write the resulting `tier:` back to state.md.
Then read the effort off it:
  | tier     | DIFF_REVIEW effort |
  | trivial  | high               |
  | normal   | high               |
  | hard     | xhigh              |
  | critical | xhigh              |
Missing or `pending` tier (a pipeline started before tiering existed) → treat as `hard`. Never
`max`, never `low`. The effort picks the agent (effort is frontmatter-only; the Agent tool has no effort parameter):
`high` → **reviewer**, `xhigh` → **reviewer-xhigh**. Print the value as `<review_effort>` in the banner. Rewrite the plan.md `**Tier:**` line per approve-plan.md's
TIER LINE, so the plan shows the tier and crew this round actually used.

BANNER RULE: finish setup and state.md edits, then print the banner as the last line before
the agent call. Both stages get one — IMPLEMENT before the implementer, DIFF_REVIEW before
the reviewer.

SEQUENCING: stages are sequential because each reads the previous stage's file output
(the reviewer reads the diff + audit.md the implementer just wrote). Invoke one subagent
per message, as its last line, and wait for it to finish — two Agent calls in one message
run in parallel and the reviewer judges files that don't exist yet. Step 2's crew seats are
the one exception: they all read the same finished diff and each writes only its own file.

1. In state.md set iteration += 1 (if iteration > max_iterations, print `■ EXIT · hit max_iterations` and STOP); set stage=implement, then (BANNER RULE) print this IMPLEMENT banner as the LAST line before invoking the implementer:
   ```
     ╭─ ⌐■-■  IMPLEMENT · 4/5 · NEO · sonnet/medium
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool: same as approve-plan.md step 1.
   Then invoke the implementer subagent: fix only "Still open". Writes audit.md.
   Set stage=diff_review.
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
   Then invoke the **test-fixer** subagent (ALWAYS opus/high, never tiered), seeded with the failing test name(s), the command, its output, and the plan's
   "Files touched" list. It writes `feature-research/<task>/repair.md` and sets `repair_verdict:`.
   Route on that verdict: `fixed` → re-run the full suite; green → step 2, still red → another
   repair round. `flake` → note it and go to step 2. `replan` or `needs-human` → print the
   fixer's report and STOP for you (the approach, not the code, is the problem).
2. CREW + DIFF_REVIEW — exactly as approve-plan.md step 2: run crew.py on the scope, record
   `crew:`, print the DIFF-REVIEW banner with the crew (pool: same as approve-plan.md step 2), run
   the crew seats in one message (lens files stamped `-r<iteration>`), then AGENT SMITH
   (**reviewer-xhigh** when `<review_effort>` is xhigh) → reads the lens reviews, appends diff
   review under `## 🔭 Review` in plan.md; sets diff_verdict.
3. Print the GATE 2 line exactly as approve-plan.md step 3 does, then STOP.
