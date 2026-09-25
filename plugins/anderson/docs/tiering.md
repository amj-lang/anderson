# Difficulty tiering — what each stage runs on, and why

Every stage has a fixed model. The tier only sizes the **effort** of the critique stages. There is
no model flag: since Opus 5.5, no stage runs on Fable (see [Why no Fable](#why-no-fable)).

## The tier

Computed once at `start.md` step 5 from the planner's `## 📈 Scorecard`, then re-computed against
the real diff at `approve-plan` / `rework`. **First match wins, top-down. Tier only escalates.**

| Tier | Rule |
|---|---|
| CRITICAL | `Risk ≥ 9` OR `Testability ≥ 7` |
| HARD | `Risk ≥ 7` OR `Coupling ≥ 7` OR `Confidence ≤ 4` OR touches security / auth / memory / concurrency / OS-fs-process |
| TRIVIAL | `Risk ≤ 2` AND `Coupling ≤ 3` AND `Confidence ≥ 8` |
| NORMAL | everything else |

Re-tier triggers at the diff gate: `≥150 lines` OR `≥8 files` → at least HARD.

CRITICAL and HARD fire on **any one** dimension going bad; TRIVIAL needs **all three** to be good.
Deliberately biased toward escalation: over-reviewing costs tokens, under-reviewing ships a bug.

## Start mode (gated)

| # | Step | Persona | trivial | normal | hard | critical |
|---|---|---|---|---|---|---|
| 1 | PLAN | THE ARCHITECT | opus/medium | opus/medium | opus/medium | opus/medium |
| 2 | GRILL | THE INTERROGATOR | you | you | you | you |
| 3 | PLAN_REVIEW → Gate 1 | THE ORACLE | opus/high | opus/high | opus/high | opus/xhigh |
| 4 | IMPLEMENT | NEO | sonnet/medium | sonnet/medium | sonnet/medium | sonnet/medium |
| 4b | REPAIR (red only) | TRINITY | opus/high | opus/high | opus/high | opus/high |
| 5 | DIFF_REVIEW → Gate 2 | AGENT SMITH | opus/high | opus/high | opus/xhigh | opus/xhigh |

## Auto mode (no gates)

| # | Step | Persona | trivial | normal | hard | critical |
|---|---|---|---|---|---|---|
| 3 | PLAN | THE ARCHITECT | opus/medium | opus/medium | opus/medium | opus/medium |
| 4 | PLAN GATE | THE ORACLE | opus/high | opus/high | opus/high | opus/xhigh |
| 6 | IMPLEMENT | NEO | sonnet/medium | sonnet/medium | sonnet/medium | sonnet/medium |
| 6b | REPAIR (red only) | TRINITY | opus/high | opus/high | opus/high | opus/high |
| 7 | DIFF PANEL | AGENT SMITH ×n | 1× sonnet/high | 2× sonnet/high | 3× opus/high | 3× opus/high |
| 7g | ARBITER | AGENT SMITH | opus/high | opus/high | opus/xhigh | opus/xhigh |

INGEST, BASELINE, RED, SHIP and REPORT are orchestrator steps: no subagent, no tiering.

## The crew (both modes)

Lens seats that join the diff review, summoned by `bin/crew.py` from the diff itself. Same
`reviewer` agent (effort `high`, one rung under the final verdict), model per seat:

| Persona | Lens | Summoned when | trivial | normal | hard | critical |
|---|---|---|---|---|---|---|
| SERAPH | security | auth/session/API/input/SQL/shell/HTML/secrets/deps touched | opus* | opus* | opus | opus |
| NIOBE | performance | queries, loops over I/O, React effects, caching touched | sonnet* | sonnet* | opus* | opus* |
| THE MEROVINGIAN | leftovers | the diff changes or removes existing code | sonnet* | sonnet* | sonnet* | sonnet* |

`*` = only when the pattern matches. SERAPH is always seated from HARD up. In auto mode, when
SERAPH sits, the `regressions+security` panel lens narrows to `regressions`.

## The rules behind the tables

- **The plan critique always runs at least one rung above the planner.** The planner is opus/medium,
  so plan-review is opus/high, and opus/xhigh at CRITICAL. `plan.md` is the reference every
  downstream check validates against: the implementer executes it verbatim and the diff reviewer
  checks the diff *against* it, so a wrong plan is invisible to everything after it. Every tier
  gets a plan critique, trivial included.
- **The planner runs at medium, not high.** It cannot be tiered (the tier comes from its own
  Scorecard), and Opus 5.5 at medium beats Opus 5 at high on coding and analysis evaluations.
- **The implementer is the cheapest model that follows a plan reliably**: sonnet/medium. Haiku is
  cheaper per token but weaker on multi-file plans, and every extra red suite buys an opus/high
  repair, which costs more than Haiku saves.
- **Repair is never tiered.** TRINITY runs opus/high on every tier. Tiering sizes *critique*, how
  much doubt a diff has to survive. A red test is a diagnosis, and a trivial-tier task with an
  undiagnosed failure is exactly as stuck as a critical one. Its budget control is the 2-round cap.
- **The diff verdict is opus/high, opus/xhigh from HARD up.** In start mode that is AGENT SMITH;
  in auto it is the arbiter, the final diff verdict there. Auto panelists run one rung under the
  arbiter (sonnet/high at TRIVIAL/NORMAL, opus/high at HARD/CRITICAL), and the arbiter backstops
  every panel outcome except a unanimous refute.
- **Effort is set by picking the agent.** `effort` lives only in agent frontmatter; the Agent tool
  takes a `model` override but no effort. So each xhigh seat has a twin agent, `plan-reviewer-xhigh`
  and `reviewer-xhigh`, with the same instructions (`test/test_agent_variants.py` fails if they
  drift) and `effort: xhigh`. Edit the base file, then copy its body into the twin.
- **Never `max`, never `low`.** `max` is uncapped thinking for a marginal gain; below medium,
  critique quality drops faster than the tokens it saves.

## Why no Fable

Opus 5.5 beats Fable 5.1 on every benchmark Anthropic published at launch (2026-09-22):

| Benchmark | Opus 5.5 | Fable 5.1 |
|---|---|---|
| Terminal-Bench 4.0 (agentic coding) | **66.4%** | 55.8% |
| CursorBench 4.0 | **57.8%** | 51.8% |
| FrontierCode v1.1 | **54.4%** | 50.3% |
| AutomationBench | **40.0%** | 31.4% |
| GDPval-AA v2.1 (Elo) | **1846** | 1735 |
| Humanity's Last Exam | **67.7%** | 65.6% |
| OSWorld 2.0 | **81.8%** | 80.7% |

It also costs 2.5× less per token (see the API pricing docs), and on a long real task (a C-to-Rust
port) it finished faster at about half Fable's cost. Anthropic's own caveat: "the gap between
Opus 5.5 and Claude Fable 5.1 is narrower than these scores suggest." Even at parity, a model at
40% of the per-token price wins every critique seat, so the `--opus` / `--fable` flags and the
`review_model` state field are gone.

What is not measured: no public head-to-head code-review benchmark exists, and these stages do
single-pass critique, not the long agentic runs the benchmarks score. If reviews start missing
things, lift effort in the thinnest seat first (NORMAL diff review) before reaching for a model.
