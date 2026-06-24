# Anderson — `auto` mode (autonomous build loop)

**Status:** v1 spec (draft) · **Type:** design doc · **Owner:** TBD

## Summary

`/anderson:auto` is a new, **additive** mode on the existing Anderson plugin. It runs the full
plan → implement → review pipeline **end-to-end with no human halts**, by replacing the interactive
human gates with independent adversarial agent panels plus an objective CI gate. It is triggered by
an external source (issue tracker, chat, CLI) and produces a **draft PR** for a human to merge.

The goal is **higher success rate on autonomous fixes**, achieved through verification independence
and executable ground truth — *not* through self-approval (which lowers success rate).

## Goals

- Run Anderson's pipeline autonomously, seeded from a task, to a reviewable draft PR.
- Raise success rate vs. naive autonomy via adversarial verification + objective CI gating.
- Stay **source-agnostic** — the mode consumes a generic `TaskSpec`; issue trackers are adapters.
- Know when *not* to attempt: bail to a human on ambiguous or out-of-scope work.

## Non-goals

- No auto-merge. A human always merges the draft PR.
- No replacement of gated/interactive Anderson — that mode stays as-is.
- Not tied to any specific issue tracker (Linear, GitHub Issues, etc. are pluggable, designed later).

## Decision: add a mode, do not rewrite

Anderson's value is its subagents (`planner`, `plan-reviewer`, `implementer`, `reviewer`) and the
rework loop. Those are unchanged between gated and autonomous use. The only difference is **who
answers the gates** — a human (interactive) vs. panels + CI (autonomous). That is a front-end swap.

| | Gated mode (today) | `auto` mode (new) |
|---|---|---|
| Subagents | planner / plan-reviewer / implementer / reviewer | **same, shared** |
| Rework loop | `/anderson:rework` | **same, shared** |
| Plan gate | human grill + approve | critic panel + criteria-coverage check |
| Diff gate | human review | reviewer panel + **CI veto** |
| Halts | yes — waits for the operator | none — runs to draft PR |
| Trigger | operator, in terminal | external source via adapter |

Shared core, two entry points. The only net-new code is the **non-halting orchestrator** that
drives the subagents and panels end-to-end. Everything it calls already exists.

```
anderson/
  agents/      planner, plan-reviewer, implementer, reviewer   ← unchanged, shared
  skills/
    start, approve-plan, approve-diff, rework   ← gated (kept untouched)
    auto                                        ← NEW: non-halting orchestrator
```

## Architecture — source-agnostic seam

`auto` mode depends only on a `TaskSpec`. Issue trackers and chat are **adapters** that produce one.
The mode never references Linear/GitHub/etc.

```
[Linear adapter]─┐
[GH issue adapter]┼──► TaskSpec ──► /anderson:auto ──► draft PR + structured report
[chat adapter]───┤
[CLI]────────────┘
```

### TaskSpec

```yaml
task:
  id:                  # stable id from the source — used for the run lock
  title:
  body:
  acceptance_criteria: # optional; derived from body if absent (+ confidence flag)
  repo:
  scope_paths:         # optional; bounds where the planner looks and where the diff may touch
```

Adapters (Linear, GitHub Issues, chat, CLI) are **out of scope for this doc** — designed later.

## Orchestrator control flow

```
1. INGEST       Normalize TaskSpec. Derive acceptance_criteria from body if absent (flag low-confidence).
                Acquire run lock on task.id (reject if a run is already active for this task).

2. BASELINE     git fetch; create isolated worktree/clone; cut a fresh branch off the LATEST default.
                Build + run the full test suite. Must be GREEN.
                Broken baseline → abort + report (never build a fix on a broken tree).

3. PLAN         planner (read-only) → plan.md, seeded with task + acceptance_criteria + scope_paths.

3a. CONFIDENCE  Planner rates task clarity. Ambiguous / underspecified / out-of-scope
    GATE        → do NOT code. Open a `needs-spec` report and stop.

4. PLAN GATE    Critic panel (3, refute lens) + acceptance-criteria coverage check.
                Clear → continue. Fixable gaps → bounded plan rework. Hard-reject → abort + report.

5. RED          Write failing test(s) encoding the acceptance criteria.
                Confirm the test is red FOR THE RIGHT REASON (asserts the behavior, not an import/
                syntax error). FREEZE the test file.

6. IMPLEMENT    implementer → make red green → audit.md.
                Implementer runs a self-review pass before the panel (cheap; cuts panel rounds).

7. DIFF GATE    Blind reviewer panel (3, fresh context — diff + plan + task only, NOT the
                implementer's self-justification) + objective checks:
                  - full suite green AND no new failures vs. baseline
                  - frozen RED test unchanged (test-tamper guard)
                  - diff within scope_paths and under size cap
                  - no forbidden-path edits; dependency changes flagged needs-human
                CI red OR ≥2/3 reviewers refute → /rework (bounded) → re-review.
                Thrash breaker: open-findings set must shrink each round, else stop + escalate.

8. SHIP         Push branch; open DRAFT PR with plan + audit trail + test results +
                self-reported confidence + residual risks. Never auto-merge.

9. REPORT       Structured result to caller: PR url, status, criteria→evidence map, blockers.
```

## Workspace isolation

- Fresh branch off the **latest** default branch (`git fetch` first — never a stale local ref).
- **Isolated worktree or fresh clone per run** so concurrent runs cannot collide on one checkout.
- Clean working tree precondition — abort if dirty.
- Branch naming: `anderson/auto/<task-id>-<short-slug>`.

## Gates & panels

### Plan critic panel (gate 4)
- 3 critics, each a distinct lens: **feasibility**, **criteria coverage**, **blast radius**.
- Prompt posture: *"Refute this plan. Find why it fails or misses an acceptance criterion.
  Default to reject if uncertain."*
- Pass requires panel clear **and** every acceptance criterion mapped to a plan step.

### Diff reviewer panel (gate 7)
- 3 reviewers, fresh context, **blind to the implementer's reasoning** (anchoring kills independence).
- Lenses: **correctness**, **does the diff match the plan?**, **regressions / security**.
- Vote: kill if ≥2/3 refute.
- **CI is a veto, not a vote** — red tests/build fail the gate regardless of votes. The one gate the
  model cannot talk its way past.

## Verification hardening

These are the additions that most affect success rate.

- **Test-tamper guard** — the RED test is frozen after step 5; a reviewer diffs the test file and
  rejects if it changed. Prevents the classic agent-TDD failure of "passing" by weakening the test.
- **Red-for-the-right-reason** — confirm the new test fails because it asserts the target behavior,
  not because of an import/syntax error. A test that errors is not a red test.
- **Full suite, no new failures** — green means the new test passes *and* there are no new failures
  vs. the baseline run. Catches regressions the fix introduces.
- **Flake handling** — compare failures against the baseline; a test already flaky at baseline is not
  "my change broke it." Re-run suspected flakes N times before trusting a red.
- **Blind reviewers** — panel sees diff + plan + task only.

## Scope & safety guardrails

- **Diff cap** — abort or flag if the diff escapes `scope_paths` or exceeds N files / M lines
  (runaway-refactor breaker).
- **Forbidden paths** — never touch CI config, `.github/`, secrets, lockfiles, or migrations unless
  the task is explicitly about them.
- **Dependency changes → mandatory human** — any manifest/lockfile change flags the PR `needs-human`,
  no exceptions (supply-chain surface).

## Loop control

- **Thrash breaker** — each rework round must shrink the open-findings set. Flat for 2 rounds → stop
  and escalate. Prevents fix-one-break-another spirals that burn the budget.
- **Finding dedup across rounds** — if the same finding recurs, the implementer is not converging →
  bail to human.
- **`max_rework_rounds`** (default ≈ 3) — still failing → stop, open a draft PR labeled `needs-human`,
  report the blocker.

## Trust & ops

- **Bail-to-human at the plan stage** (gate 3a) — knowing when *not* to attempt is a top success-rate
  lever. A confident wrong fix is worse than no fix.
- **Full audit trail in the PR** — every gate decision, vote, finding, and rework round → PR body /
  `audit.md`. The human merging needs to see *why the bot believes it is done*.
- **Self-reported confidence + residual risks** in the PR description, so the reviewer can triage fast.
- **Run lock per `task.id`** — a double-trigger must not spawn two runs / two PRs.
- **Stage checkpoints** — a crash or re-trigger resumes rather than redoing prior stages
  (cost + idempotency).
- **Per-run budget cap** (tokens / time) — abort + report if blown.

## Safety boundaries (non-negotiable)

- Draft PR only. Never auto-merge.
- Branch only — never push to the default branch.
- Baseline-green precondition — never apply a fix on a broken tree.
- Forbidden-path and dependency guards as above.
- Secrets: run needs an Anthropic key + a repo-scoped token (contents + PR write). Do not reuse
  source-adapter credentials.

## Why this improves success rate

The gain comes from three things, none of which is "remove the human":

1. **Objective ground truth** — a failing repro test (RED) + full-suite CI is a gate the model cannot
   rationalize past.
2. **Verification independence** — fresh-context, blind, adversarial panels prompted to *refute*,
   majority-vote, with diverse lenses.
3. **Loop until clean** — bounded rework with a thrash breaker.

Self-approval (the same model rubber-stamping its own work) does the opposite — it inflates confidence
and ships confident-wrong fixes. `auto` mode deliberately avoids it.

## Open questions

1. **Runner** — GitHub Actions (CI gate = the workflow itself, native `gh` auth) vs. a long-running
   worker. Shapes how steps 2 and 7 execute the suite.
2. **RED step universality** — always (bug fix → yes; feature → test encodes criteria), or
   feature-exempt?
3. **Acceptance criteria** — require as input (stronger spec, less autonomous) vs. always derive
   (more autonomous, weaker). Current default: derive-if-absent + confidence flag.
4. **Panel size / threshold** — start at 3 / majority-refute, tune later.
5. **Difficulty routing** — size the harness to estimated task difficulty (trivial fix shouldn't pay
   for full panels)? Likely a v2 optimization.

## Out of scope (later)

- Source adapters (Linear, GitHub Issues, chat) and their auth.
- Difficulty-based harness sizing.
