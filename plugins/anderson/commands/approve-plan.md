---
description: "Approve the plan, run implement then diff-review, then halt."
argument-hint: <task-slug>
effort: medium
---
Task slug = "$ARGUMENTS"; the task key (state dir name) is its LAST `/`-segment, so a pasted
branch name like `user/ar-123-title` resolves to `feature-research/ar-123-title/`.
In state.md set plan_verdict=ship, gate=none, iteration += 1.
If iteration > max_iterations, print `EXIT · hit max_iterations`, log the run
(`python3 "${CLAUDE_PLUGIN_ROOT}/bin/runlog.py" feature-research/<task> --mode gated --outcome aborted:max_iterations`) and STOP.

DIFF REVIEW SEAT: derived from state.md `tier`; no flag, no state field.
RE-TIER FIRST — before reading the seat, re-tier and take the MAX (tier only ever escalates,
never drops). Two inputs. The plan's `## 📈 Scorecard`: apply the tier rule of
`/anderson:start` to the Reviewer column where the plan-reviewer filled it (a plan the reviewer
scored above Risk 2, above Coupling 3 or below Confidence 8 is not TRIVIAL). And the ACTUAL
diff, measured after the implementer returns (step 1): `git diff --stat` showing ≥400 changed lines OR ≥15 files (tests, lockfiles
and generated files excluded; "generated" = marked `linguist-generated` in `.gitattributes` or carrying a generated / do-not-edit header; vendored and minified code counts toward the size.) → at least HARD; a diff that alters an
auth/permission check, secret/crypto handling, locking/concurrency, or builds a shell command /
filesystem path from external input, or adds/changes an externally reachable entry point
(HTTP route, server action, RPC/GraphQL resolver, webhook, CLI/IPC handler) or the input
validation in front of one → at least HARD. Write the resulting `tier:` back to state.md.
Then read the seat off it:
  | tier     | DIFF_REVIEW | agent          |
  | trivial  | none        | NO DIFF REVIEW |
  | normal   | opus/high   | reviewer       |
  | hard     | fable/high  | reviewer-fable |
  | critical | fable/high  | reviewer-fable |
Missing or `pending` tier (a pipeline started before tiering existed) → treat as `hard`. Model
and effort live in agent frontmatter (which the band reads), so the tier picks the agent.
NO DIFF REVIEW (TRIVIAL): the plan was reviewed, the tests are green, the typecheck and lint ran,
and Gate 2 puts the diff in front of you. No crew, no AGENT SMITH. A trivial plan whose diff
re-tiers higher gets the full review of its new tier.

TIER LINE: a re-tier that does not show up in the plan is a silent price change. After writing
`tier:` back to state.md, rewrite the `**Tier:**` line under the plan.md H1 to:
  `**Tier:** <TIER> — implement sonnet/medium · diff_review <model/effort | none>`
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
2. RE-TIER on the diff (above), then branch on the tier. TRIVIAL → skip to step 3: set
   `diff_verdict: unreviewed` and `crew: none` in state.md, `gate: human`, and print the trivial
   Gate 2 card. Any other tier → the crew and AGENT SMITH:
   CREW — who joins AGENT SMITH on this diff. Scope = the union of plan.md "Files touched",
   audit.md "Files changed", and repair.md "Outside the plan's files" (when it exists). From the
   repo root run `python3 "${CLAUDE_PLUGIN_ROOT}/bin/crew.py" <tier> --hint <lenses> <scope files>`,
   the lenses taken from plan.md's `**Crew hint:**` line (drop `--hint` when it says `none`): one line per
   summoned lens, `<lens> <PERSONA> <agent> <model/effort> <reason>`, or `none` (Smith reviews alone). Routing is
   pattern matching in the script, never a model call. Record `crew: <PERSONA + PERSONA | none>`
   in the state.md STATE block.
   Then, unless the crew is `none`, invoke one subagent per crew line IN ONE MESSAGE (the one
   parallel call in this command: each seat writes only its own file), using the agent the line
   names (`reviewer` or `reviewer-medium`, both opus) and
   framing each: "You are <PERSONA>, the <lens> lens seat on the diff
   review of task <task>. Scope: <scope files>. Review through your lens only; do NOT read
   audit.md or any other review. Write ONLY `feature-research/<task>/review-<lens>-r<iteration>.md`;
   do not touch plan.md or state.md." Wait for every seat.
   Then invoke the **reviewer** subagent as AGENT SMITH (**reviewer-fable** at HARD and
   CRITICAL) → reads the lens reviews, appends diff review under `## 🔭 Review`
   in plan.md; sets diff_verdict.
3. Print the GATE 2 TL;DR card and STOP. Fill EVERY value for real (slug, verdict, criteria
   counts from the diff review's `criteria:` line — copy-pasteable, no literal `<task>`); when
   criteria failed, list each on its own indented line with the reviewer's one-line why:
   ```
   🔴 GATE 2 · AWAITING YOU
     criteria <proven>/<N> proven<, failed: #<n> <one-line why> — or " (all)">
     tier <TIER><, was <old> — or ""> · reviewed by <model/effort> · crew <PERSONA + … | none>
     verdict <diff_verdict> → read the diff (`! git diff HEAD` · new files `! git status -s` ·
     fleet `o`) + plan.md ## 🔭 Review, then
     /anderson:approve-diff <task> to ship, or /anderson:rework <task>.
   ```
   TRIVIAL card (no diff review ran; the counts come from the Evidence column and audit.md):
   ```
   🔴 GATE 2 · AWAITING YOU
     criteria <filled>/<N> with evidence · tests <green | n/a> · typecheck + lint <clean | n/a>
     tier TRIVIAL · no diff review: you are the reviewer
     → read the diff (`! git diff HEAD` · new files `! git status -s` · fleet `o`), then
     /anderson:approve-diff <task> to ship, or tell me what to change.
   ```
   A change you ask for at this card goes to the implementer as "Still open" (the rework loop).
   Halt is unconditional even on a ship verdict.
