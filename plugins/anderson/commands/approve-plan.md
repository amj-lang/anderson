---
description: "Approve the plan, run implement then diff-review, then halt."
argument-hint: <task-slug>
---
Task slug = "$ARGUMENTS"; the task key (state dir name) is its LAST `/`-segment, so a pasted
branch name like `user/ar-123-title` resolves to `feature-research/ar-123-title/`.
In state.md set plan_verdict=ship, gate=none, iteration += 1.
If iteration > max_iterations, print `EXIT · hit max_iterations`, log the run
(`python3 "${CLAUDE_PLUGIN_ROOT}/bin/runlog.py" feature-research/<task> --mode gated --outcome aborted:max_iterations`) and STOP.

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
`high` → **reviewer**, `xhigh` → **reviewer-xhigh**.

TIER LINE: a re-tier that does not show up in the plan is a silent price change. After writing
`tier:` back to state.md, rewrite the `**Tier:**` line under the plan.md H1 to:
  `**Tier:** <TIER> — implement sonnet/medium · diff_review opus/<review_effort>`
and note the escalation inline when the tier changed (`was <old>: <one-line why>`).

SEQUENCING: stages are sequential because each reads the previous stage's file output
(the reviewer reads the diff + audit.md the implementer just wrote). Invoke one subagent
per message, as its last line, and wait for it to finish — two Agent calls in one message
run in parallel and the reviewer judges files that don't exist yet. Step 2's crew seats are
the one exception: they all read the same finished diff and each writes only its own file.

1. Set stage=implement, then invoke the **implementer** subagent: execute plan.md; on
   a rework loop fix only "Still open". Writes audit.md. Set stage=diff_review.
1b. TESTS RED? — the implementer gets ONE try at a failing test, then TRINITY takes it.
   After the implementer returns, run the repo's test command. GREEN → step 2. RED → set
   `stage: repair`, `repair_round:` += 1 (abort to you at `repair_round > 2`, reason
   `repair-budget`), then invoke the **test-fixer** subagent (ALWAYS opus/high, never tiered), seeded with the failing test name(s), the command, its output, and the plan's
   "Files touched" list. It writes `feature-research/<task>/repair.md` and sets `repair_verdict:`.
   Route on that verdict: `fixed` → re-run the full suite; green → step 2, still red → another
   repair round. `flake` → note it and go to step 2. `replan` or `needs-human` → print the
   fixer's report and STOP for you (the approach, not the code, is the problem).
2. CREW — who joins AGENT SMITH on this diff. Scope = the union of plan.md "Files touched",
   audit.md "Files changed", and repair.md "Outside the plan's files" (when it exists). From the
   repo root run `python3 "${CLAUDE_PLUGIN_ROOT}/bin/crew.py" <tier> --hint <lenses> <scope files>`,
   the lenses taken from plan.md's `**Crew hint:**` line (drop `--hint` when it says `none`): one line per
   summoned lens, `<lens> <PERSONA> <agent> <model/effort> <reason>`, or `none` (Smith reviews alone). Routing is
   pattern matching in the script, never a model call. Record `crew: <PERSONA + PERSONA | none>`
   in the state.md STATE block.
   Then, unless the crew is `none`, invoke one subagent per crew line IN ONE MESSAGE (the one
   parallel call in this command: each seat writes only its own file), using the agent the line
   names (`reviewer` or `reviewer-medium`, both opus; effort lives in their frontmatter) and
   framing each: "You are <PERSONA>, the <lens> lens seat on the diff
   review of task <task>. Scope: <scope files>. Review through your lens only; do NOT read
   audit.md or any other review. Write ONLY `feature-research/<task>/review-<lens>-r<iteration>.md`;
   do not touch plan.md or state.md." Wait for every seat.
   Then invoke the **reviewer** subagent as AGENT SMITH (**reviewer-xhigh** when
   `<review_effort>` is xhigh) → reads the lens reviews, appends diff review under `## 🔭 Review`
   in plan.md; sets diff_verdict.
3. Print the GATE 2 TL;DR card and STOP. Fill EVERY value for real (slug, verdict, criteria
   counts from the diff review's `criteria:` line — copy-pasteable, no literal `<task>`); when
   criteria failed, list each on its own indented line with the reviewer's one-line why:
   ```
   🔴 GATE 2 · AWAITING YOU
     criteria <proven>/<N> proven<, failed: #<n> <one-line why> — or " (all)">
     tier <TIER><, was <old> — or ""> · reviewed by opus/<review_effort> · crew <PERSONA + … | none>
     verdict <diff_verdict> → read the diff (`! git diff HEAD` · new files `! git status -s` ·
     fleet `o`) + plan.md ## 🔭 Review, then
     /anderson:approve-diff <task> to ship, or /anderson:rework <task>.
   ```
   Halt is unconditional even on a ship verdict.
