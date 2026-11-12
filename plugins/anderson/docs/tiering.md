# Difficulty tiering — what each stage runs on, and why

Every stage has a fixed seat per tier. The tier sizes the **critique**: how many reviews run and
on which model. There is no model flag. Opus 5.5 is the default seat; Fable 5.2 takes the seats
where a wrong call is most expensive (see [Where Fable sits](#where-fable-sits)); TRIVIAL drops
the diff review altogether (see [The short path](#the-short-path-trivial)).

## The tier

Computed at `start.md` step 3b from the planner's `## 📈 Scorecard` (before the grill, which it
also sizes), then re-computed at `approve-plan` / `rework` against the plan-reviewer's scores and
the real diff. **First match wins, top-down. Tier only escalates.**

| Tier | Rule |
|---|---|
| CRITICAL | `Risk ≥ 9` |
| HARD | `Risk ≥ 7` OR `Coupling ≥ 8` OR `Confidence ≤ 3` OR `Testability ≥ 7` OR the change *alters* an auth/permission check, secret/crypto handling, locking/concurrency, or builds a shell command / filesystem path from external input OR adds/changes an externally reachable entry point (HTTP route, server action, RPC/GraphQL resolver, webhook, CLI/IPC handler) or the input validation in front of one |
| TRIVIAL | `Risk ≤ 2` AND `Coupling ≤ 3` AND `Confidence ≥ 8` |
| NORMAL | everything else |

Re-tier triggers at the diff gate: the tier rule applied to the Scorecard's Reviewer column
(a plan the reviewer scored out of TRIVIAL gets a diff review), and `≥400` changed lines OR `≥15 files`, excluding tests, lockfiles and generated files → at least HARD. "Generated" = marked `linguist-generated` in `.gitattributes` or carrying a generated / do-not-edit header; vendored and minified code counts toward the size.

CRITICAL and HARD fire on **any one** dimension going bad; TRIVIAL needs **all three** to be good.
Deliberately biased toward escalation: over-reviewing costs tokens, under-reviewing ships a bug.
A change that only *touches* a sensitive area no longer escalates by itself; one that alters it does.

### Calibration

The old rules (CRITICAL on high Testability, HARD on Coupling 7 or Confidence 4 and below or any touch
of a sensitive area, re-tier at 150 lines / 8 files counting everything) put 25 of 31 tiered runs at
HARD or CRITICAL, so nearly every diff review ran opus/xhigh. Evidence from `runs.jsonl` (32 lines):

| Tier | Runs | Rework (`rework_rounds > 0`) |
|---|---|---|
| critical | 5 | 3/5 |
| hard | 20 | 15/20 |
| normal | 2 | 0/2 |
| trivial | 4 | 0/4 |
| pending (aborted) | 1 | 0/1 |

Auto runs tagged `runaway` (over 200 lines or 20 files): 4 of 5 shipped, so a typical diff already
cleared the old 150-line trigger. Rework at hard is confounded (xhigh raises more findings), so it
does not show the tier was right. `runlog.py --summary` now prints median tokens, median time and
rework rate per tier, so the next recalibration reads cost off the log.

Replay of the logged runs with a GitHub PR under the new rules: 15 of 32 runs replayable (17 skipped: private repos, GitLab, no Scorecard in the PR body). HARD+CRITICAL: old rules 14/15, new rules with an over-firing path/diff heuristic for the sensitive and entry-point clauses 13/15 (target was half or fewer, **missed**), new rules on Scorecard and size alone 7/15 (normal 5, hard 7). The heuristic matches crew.py's security patterns plus route/action/handler paths, so it is an upper bound: the entry-point and sensitive clauses, not the Scorecard thresholds, now decide most HARDs. Thresholds were not tuned to fit; the next recalibration reads the real cost and scorecards from `runs.jsonl`.

## Start mode (gated)

| # | Step | Persona | trivial | normal | hard | critical |
|---|---|---|---|---|---|---|
| 1 | PLAN | THE ARCHITECT | opus/medium | opus/medium | opus/medium | opus/medium |
| 2 | GRILL | THE INTERROGATOR | you (LB rows only) | you | you | you |
| 3 | PLAN_REVIEW → Gate 1 | THE ORACLE | opus/medium | opus/high | opus/high | fable/high |
| 4 | IMPLEMENT | NEO | sonnet/medium | sonnet/medium | sonnet/medium | sonnet/medium |
| 4b | REPAIR (red only) | TRINITY | opus/high | opus/high | opus/high | opus/high |
| 5 | DIFF_REVIEW → Gate 2 | AGENT SMITH | NO DIFF REVIEW (you) | opus/high | fable/high | fable/high |

## Auto mode (no gates)

| # | Step | Persona | trivial | normal | hard | critical |
|---|---|---|---|---|---|---|
| 3 | PLAN | THE ARCHITECT | opus/medium | opus/medium | opus/medium | opus/medium |
| 4 | PLAN GATE | THE ORACLE | opus/medium | opus/high | opus/high | fable/high |
| 6 | IMPLEMENT | NEO | sonnet/medium | sonnet/medium | sonnet/medium | sonnet/medium |
| 6b | REPAIR (red only) | TRINITY | opus/high | opus/high | opus/high | opus/high |
| 7 | DIFF REVIEW | AGENT SMITH | NO DIFF REVIEW (CI veto only) | opus/high | 3× opus/high panel | 3× opus/high panel |
| 7g | ARBITER | AGENT SMITH | — | — | fable/high | fable/high |

INGEST, BASELINE, RED, SHIP and REPORT are orchestrator steps: no subagent, no tiering.

## The crew (both modes)

Lens seats summoned by `bin/crew.py` at both reviews. At plan review (`--plan`) SERAPH and NIOBE
judge the design before THE ORACLE, which confirms or rejects each finding and folds it into
plan.md: a missing authorization check or an N+1 query is one plan edit there, a rework round
after the code exists. Routing reads the plan's "Files touched" paths and its text (no diff yet);
THE MEROVINGIAN sits only at diff review, since orphans need a diff and the plan-reviewer's
blast-radius check covers planned dead code. Plan-review seats are pattern-matched from NORMAL up
(they confirmed 21 of 28 findings at NORMAL): SERAPH opus/high, NIOBE opus/medium below HARD and
opus/high from HARD up. At TRIVIAL only the plan's `**Crew hint:**` seats a lens, at either review.

At diff review the crew is summoned from the diff itself, **from HARD up only**: below HARD the
pattern seats confirmed 0 of 6 findings in `runs.jsonl` (0.74.0), so only the plan's `**Crew hint:**`
seats a lens there. Same
`reviewer` prompt, always on opus; the effort picks the agent (`reviewer-medium` or `reviewer`):

| Persona | Lens | Summoned when | trivial | normal | hard | critical |
|---|---|---|---|---|---|---|
| SERAPH | security | auth/session/API/input/SQL/shell/HTML/secrets/deps touched | — | hint | opus/high | opus/high |
| NIOBE | performance | queries, loops over I/O, React effects, caching touched | — | hint | opus/high* | opus/high* |
| THE MEROVINGIAN | leftovers | the diff changes or removes existing code | — | hint | opus/high* | opus/high* |

`*` = only when the pattern matches. `hint` = only when the plan's Crew hint names it (SERAPH
opus/high, the others opus/medium). `—` = no diff review runs at TRIVIAL, so no seat. The crew
stays on Opus at every tier: a lens is a narrow question, and Fable is spent on the one seat
that rules on everything. SERAPH is always seated from HARD up. In auto mode, when
SERAPH sits, the `regressions+security` panel lens narrows to `regressions`.

## The rules behind the tables

- **A harder tier buys a stronger model, not more effort.** Until 0.75 the escalation seat was
  opus/xhigh. Anthropic's guidance for Opus 5.5 is to keep `xhigh` for work with a measured gain
  (it thinks much longer per turn there), and for Fable 5.2 that most of the gain arrives by
  `high`. So the escalation seat is now fable/high, and nothing runs at `xhigh`.
- **Every tier gets a plan critique.** `plan.md` is the reference every downstream check validates
  against: the implementer executes it verbatim and the diff reviewer checks the diff *against*
  it, so a wrong plan is invisible to everything after it. NORMAL and HARD review it one rung
  above the planner (opus/high), CRITICAL on fable/high. TRIVIAL reviews it at the planner's own
  opus/medium: a second, independent read of a short plan, not a deeper one.
- **The planner runs at medium, not high.** It cannot be tiered (the tier comes from its own
  Scorecard), and Opus 5.5 at medium beats Opus 5 at high on coding and analysis evaluations.
- **The implementer is the cheapest model that follows a plan reliably**: sonnet/medium, which is
  also Anthropic's starting point for agentic coding on Sonnet 5.5. Haiku is cheaper per token
  but weaker on multi-file plans, and every extra red suite buys an opus/high repair, which
  costs more than Haiku saves.
- **Repair is never tiered.** TRINITY runs opus/high on every tier. Tiering sizes *critique*, how
  much doubt a diff has to survive. A red test is a diagnosis, and a trivial-tier task with an
  undiagnosed failure is exactly as stuck as a critical one. Its budget control is the 2-round cap.
- **The diff verdict is opus/high at NORMAL, fable/high from HARD up, absent at TRIVIAL.** At
  NORMAL both modes run AGENT SMITH alone. From HARD up, start mode runs SMITH on fable/high; auto
  runs a 3× opus/high panel and a fable/high arbiter that backstops every outcome except a
  unanimous refute. A sub-HARD auto panel only fed an arbiter that re-reviewed the diff anyway.
- **The seat is set by picking the agent.** The Agent tool takes a per-call `model` and `effort`,
  but the band reads both from agent frontmatter (the spawn event carries no effort), so each
  off-default seat keeps a twin agent (`plan-reviewer-fable`, `plan-reviewer-medium`,
  `reviewer-fable`, `reviewer-medium`) with the same instructions
  (`test/test_agent_variants.py` fails if they drift) and its own `model:` / `effort:`. Edit the
  base file, then copy its body into every twin.
- **Never `max`, never `xhigh`, never `low` on a pipeline agent.** `max` is uncapped thinking for
  a marginal gain; `xhigh` has no measured gain here; below medium, critique quality drops faster
  than the tokens it saves.
- **The orchestrator runs at medium.** `/anderson:start`, `approve-plan`, `rework` and
  `approve-diff` set `effort: medium` in their frontmatter (it lasts for that turn only): they
  route, dispatch and print cards. A main session left at `high` on Fable thinks before every
  step of that routing. `/anderson:auto` keeps the session's own effort: it is one long
  unattended turn, and lower effort stops early more often.

## The short path (TRIVIAL)

A TRIVIAL plan (Risk ≤ 2, Coupling ≤ 3, Confidence ≥ 8, and nothing the HARD rule catches) runs
four steps and no more: **plan → grill → plan review → implement**.

| Step | What runs at TRIVIAL |
|---|---|
| plan | opus/medium, told to keep a trivial plan short |
| grill | only LB decisions and `derived` criteria reach you; none of either, no conversation |
| plan review | opus/medium, no crew seats unless the plan's Crew hint names one |
| implement | sonnet/medium, with its own tests, typecheck and lint |
| diff review | NO DIFF REVIEW: Gate 2 shows you the diff (auto: CI veto + frozen test, then the draft PR) |

Why it is safe to skip the diff review there, and only there:
- The tier is checked three times. The planner scores it, the plan-reviewer re-scores it in the
  Reviewer column, and the real diff is measured. Any one of them above TRIVIAL brings the diff
  review back; the tier only escalates.
- The HARD rule runs first, so a change to auth, secrets, concurrency or an entry point is never
  TRIVIAL, whatever its scores.
- The 4 trivial runs in `runs.jsonl` had 0 rework rounds: the diff review found nothing to send
  back at this tier.
- You still read the diff at Gate 2 (gated) or on the draft PR (auto), and both say no review ran.

A change you can already see (a typo, a renamed label, a one-line fix) does not need anderson at
all: ask for it directly. The pipeline starts paying for itself when the plan is worth reviewing.

## Where Fable sits

| Seat | Tier | Was (0.53 to 0.75) | Now |
|---|---|---|---|
| Plan review (THE ORACLE) | CRITICAL | opus/xhigh | fable/high |
| Diff review (AGENT SMITH), start mode | HARD, CRITICAL | opus/xhigh | fable/high |
| Arbiter, auto mode | HARD, CRITICAL | opus/xhigh | fable/high |

Everything else stays where it was: Opus for the planner, the NORMAL reviews, the panel, the
crew and repair; Sonnet for the implementer and the prototyper.

Why these seats and no others. Anthropic's own guidance on Fable 5.2 is that Opus 5.5 stays the
default for most workloads, and Fable is for when Opus at higher effort still falls short. That
is the definition of the escalation seat: the tier already says this change needs more than
opus/high. Fable 5.2 costs about twice Opus 5.5 per token (API pricing docs), so it sits where one
verdict decides whether a risky diff ships, not on every seat. It runs at `high` because most
of its gain arrives by `high` and the levels above it are uneven.

History: 0.53.0 dropped Fable entirely, because Opus 5.5 beat Fable 5.1 on every launch benchmark
at 2.5× less per token. Fable 5.2 is a different model at a lower price, and it comes back only
into the seats above.

What is not measured: no public head-to-head code-review benchmark exists, and this placement
follows published guidance, not our own runs. `runlog.py --summary` prints rework rate and median
tokens per tier; compare HARD before and after 0.76.0 before moving Fable to more seats or
taking it off these. Fable 5.2 also runs safety classifiers that can decline security-heavy
work; SERAPH stays on Opus, and a declined review falls back per your Claude Code settings.

## Model IDs

Use bare model-ID strings, no date suffixes; pricing lives in the API docs, not here.
