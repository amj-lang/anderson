# Anderson — `auto` mode (autonomous build loop)

How auto mode works and why. The executable source of truth is `commands/auto.md`; version history is in `CHANGELOG.md`.

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
  source_url:          # optional; the ticket link (Linear/GitHub/Jira/…). Rendered at the TOP of
                       # the PR body when present; omitted (never fabricated) when absent.
  repo:                # the primary repo
  repos:               # optional; additional repos the task must change → one branch + PR per repo
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
                Plan enumerates failure paths in 🧯 Error handling, each deduced / needs-context.

3a. CONFIDENCE  Planner rates task clarity. Ambiguous / underspecified / out-of-scope
    GATE        → do NOT code. Open a `needs-spec` report and stop.

4. PLAN GATE    Critic panel (3, refute lens) + acceptance-criteria coverage check.
                Clear → continue. Fixable gaps → bounded plan rework. Hard-reject → abort + report.

5. RED          Write failing test(s) encoding the acceptance criteria.
                Confirm the test is red FOR THE RIGHT REASON (asserts the behavior, not an import/
                syntax error). FREEZE the test file.

6. IMPLEMENT    implementer → make red green → audit.md.
                Implementer runs a self-review pass before the panel (cheap; cuts panel rounds).
                ONE try at a failing test, then it reports `tests-red` and stops.

6b. REPAIR      test-fixer (TRINITY, opus/high, always) — ONLY when tests are red.
    (conditional) Reproduce → flake-check → name the root cause → smallest fix in production code
                → single test AND full suite green. Never weakens, skips or deletes a test; the
                frozen-test tamper guard still applies at gate 7. Verdicts: fixed / flake /
                replan (→ replan bounce) / needs-human. Budget 2 rounds, then escalate.
                Sequential with the panel by construction — it edits the tree reviewers read.

7. DIFF GATE    Blind reviewer panel (3, fresh context — diff + plan + task only, NOT the
                implementer's self-justification) + objective checks:
                  - full suite green AND no new failures vs. baseline
                  - frozen RED test unchanged (test-tamper guard)
                  - diff within scope_paths and under size cap
                  - no forbidden-path edits; dependency changes flagged needs-human
                CI red → REPAIR (6b), not the rework loop — a red build is a diagnosis problem.
                ≥2/3 reviewers refute → /rework (bounded) → re-review.
                Thrash breaker: open-findings set must shrink each round, else stop + escalate.

8. SHIP         Push branch; open DRAFT PR with plan + audit trail + test results +
                self-reported confidence + residual risks. Never auto-merge.

9. REPORT       Structured result to caller: PR url, status, criteria→evidence map, open questions,
                blockers.
```

## Workspace isolation

- Fresh branch off the **latest** default branch (`git fetch` first — never a stale local ref).
- **Isolated git worktree (or fresh clone) per repo** so a run never disturbs in-flight work and
  concurrent runs cannot collide on one checkout. A DIRTY working tree → use a worktree rather than
  aborting (the earlier "abort if dirty" rule); a CLEAN tree may branch in place.
- **Multi-repo:** when the task must change repos beyond the current one (`repos:` in the TaskSpec,
  scope spilling outside the repo, or a sibling repo recorded in project memory / `CLAUDE.md`),
  isolate a worktree per repo, branch each off its latest default, and open **one draft PR per repo**
  — cross-linked (`Companion PRs:` on the primary, `Part of <task-id>` on each companion) and
  labeled `needs-human` (cross-repo is higher-risk by default).
- Branch naming (every repo): `anderson/auto/<task-id>-<short-slug>`.

## Gates & panels

Plan errors are cheap to fix (you rework, nothing ships), so the plan gate is one reviewer and the
rigor budget sits at the diff gate, sized by tier.

### Plan gate (gate 4)
- Mechanical criteria-coverage check + **one** `plan-reviewer` with a refute posture: *"Refute this
  plan. Find why it fails or misses an acceptance criterion. Default to reject if uncertain."*
- **Runs on every tier** (opus/high; opus/medium at trivial, fable/high at critical). Pass requires `ship` **and** every acceptance criterion
  mapped to a plan step. One bounded plan-rework on failure, then abort.

### Diff gate (gate 7)
- **CI is a veto, not a vote**: it runs FIRST and a red build short-circuits before any reviewer
  tokens are spent. The one gate the model cannot talk its way past.
- **Trivial: no diff review.** The CI veto, the frozen test and the tamper guard are the gate;
  the draft PR states that no review ran. The tier is re-checked first against the plan-reviewer's
  scores and the real diff, and any escalation brings the review back.
- **Normal: AGENT SMITH alone** (opus/high), blind to the implementer's reasoning, judging
  correctness, regressions/security and plan-match in one pass. His verdict is the gate. A sub-HARD
  panel only fed an arbiter that re-reviewed the diff anyway, so it was pure cost.
- **Hard/critical: 3 blind panelists + arbiter.** Three `reviewer`s (opus/high), one lens each, run
  in parallel, blind to `audit.md` and to each other. One fable/high arbiter runs on every outcome
  except a unanimous refute: it resolves a split **on merit, not headcount**, and signs off a
  unanimous *ship* by re-reviewing independently, justified in a required `## Options considered`
  (+/−) table.

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
- **Red suite ≠ rework** — the rework loop carries REVIEW findings to the implementer. A red test or
  a red build goes to the test-fixer (step 6b) on its own 2-round budget, because looping a
  sonnet implementer on a failure it never root-caused is how tests get skipped, loosened or deleted.
- **`max_rework_rounds`** (default ≈ 3) — still failing → stop, open a draft PR labeled `needs-human`,
  report the blocker.

## Trust & ops

- **Bail-to-human at the plan stage** (gate 3a) — knowing when *not* to attempt is a top success-rate
  lever. A confident wrong fix is worse than no fix.
- **Full audit trail in the PR** — every gate decision, vote, finding, and rework round → PR body /
  `audit.md`. The human merging needs to see *why the bot believes it is done*.
- **Self-reported confidence + residual risks** in the PR description, so the reviewer can triage fast.
- **Open questions & assumptions in the PR** — the `needs-context` failure paths auto could not decide
  without a human (and the assumptions it did make) are listed in the PR + flag it `needs-human`. Auto
  ships the question, never an invented business answer.
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
