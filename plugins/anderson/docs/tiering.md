# Difficulty tiering — why the review gates cost what they cost

`/anderson:start` used to spend the same on every task: a plan critique at `xhigh` and a diff
critique at `high`, whatever the change was. A one-line copy fix and a schema migration got the
same two Fable calls. This document is why that changed and how the replacement is calibrated.

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

Note the asymmetry. CRITICAL and HARD fire on **any one** dimension going bad; TRIVIAL needs
**all three** to be good. Deliberately biased toward escalation — the cost of over-reviewing is
tokens, the cost of under-reviewing is a bug you ship.

## The effort table

| Tier | PLAN_REVIEW | DIFF_REVIEW |
|---|---|---|
| TRIVIAL | *skipped* | medium |
| NORMAL | high | medium |
| HARD | xhigh | high |
| CRITICAL | xhigh | xhigh |

### Why the plan critique runs one rung above the diff critique

`plan.md` is the reference every downstream check validates against. The implementer executes it
verbatim ("no scope additions"). The diff reviewer checks the diff *against* it. So a wrong plan
is invisible to everything after it — a correct diff review will happily pass the wrong thing.

A missed diff bug still faces CI, the implementer's tests, and the human at Gate 2. A missed plan
error faces nothing. Asymmetric escape probability, asymmetric effort.

This is the opposite of the rule in `auto.md` ("rigor budget is spent at the diff gate"), and the
divergence is deliberate: auto's diff gate is a 3-reviewer blind panel plus an arbiter, so it can
afford to be diff-heavy. Start mode's diff gate is one reviewer and a card you read.

### Why the band is medium → xhigh

From the Fable 5.1 effort benchmark (score, tokens/task):

| Effort | Score | Tokens |
|---|---|---|
| max | 73.4% | 72,060 |
| xhigh | 72.8% | 51,349 |
| high | 69.4% | 33,153 |
| medium | 68.0% | 23,801 |
| low | 66.2% | 19,522 |

Marginal cost of stepping down, in points lost per 1k tokens saved:

| Step | Points | Tokens | Cost |
|---|---|---|---|
| xhigh → high | 3.4 | 18,196 | 0.19 /1k |
| high → medium | 1.4 | 9,352 | **0.15 /1k** |
| medium → low | 1.8 | 4,279 | 0.42 /1k |

**Never `max`** — buys +0.6 points over xhigh for +20,711 tokens. **Never `low`** — quality falls
off a cliff below medium, at nearly 3× the marginal cost of the rung above it.

### Why the model stays Fable

Every Opus 5 configuration except `low` is strictly dominated — a Fable config scores higher on
fewer tokens:

| Opus | Score | Tokens | Beaten by | Score | Tokens |
|---|---|---|---|---|---|
| medium | 64.3% | 23,612 | Fable low | 66.2% | 19,522 |
| high | 66.7% | 27,932 | Fable medium | 68.0% | 23,801 |
| xhigh | 69.3% | 54,239 | Fable high | 69.4% | **33,153** |
| max | 70.0% | 61,838 | Fable high | 69.4% | 33,153 |

Opus takes more steps to reach the same answer (72 vs 55 at xhigh), and steps are tokens. So
`--opus` is an **escape valve for an exhausted Fable budget**, not a quality upgrade. Reach for it
when the Fable sub-cap is spent and the work cannot wait, and understand you are paying more
tokens for a worse review.

## What it saves

Baseline was 84,502 tokens/task (xhigh plan + high diff), identical for every task.

| Tier | Now | Was | Δ |
|---|---|---|---|
| TRIVIAL | 23,801 | 84,502 | **−72%** |
| NORMAL | 56,954 | 84,502 | **−33%** |
| HARD | 84,502 | 84,502 | 0% |
| CRITICAL | 102,698 | 84,502 | **+22%** |

HARD lands on exactly the old budget. TRIVIAL and NORMAL get cheaper; CRITICAL gets more than it
used to, which is the point — the old `Risk ≥ 8` escalation ignored Testability, Coupling and
Confidence entirely, so a task that could not be verified without a human got a plain `high`
review unless its Risk score happened to clear 8.

At a 15/55/25/5 tier mix that is roughly **−28% Fable tokens per task**.

## Caveat

The benchmark measures agentic coding (70-78 steps/task, the model doing the work). These stages
do single-pass critique. The ordering should hold; the exact point deltas should not be trusted to
two decimals. If NORMAL diff reviews start missing things, that is the tier to lift first — it is
the thinnest automated check in the pipeline.
