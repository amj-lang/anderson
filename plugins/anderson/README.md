# anderson

[![ci](https://github.com/amj-lang/anderson/actions/workflows/ci.yml/badge.svg)](https://github.com/amj-lang/anderson/actions/workflows/ci.yml)
[![version](https://img.shields.io/badge/version-0.56.0-blue)](https://github.com/amj-lang/anderson)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A2BE2)](https://github.com/amj-lang/anderson)

**Four Claude subagents that plan, grill, implement, and review each other — with two human gates, because green ≠ understood.**

A gated maker/checker loop: one task at a time, per-stage model+effort, state on disk, ships a real PR. Two unconditional human gates mean nothing merges without your eyes on it.

## auto mode (experimental)

`/anderson:auto <task-id> <title> [body|@taskspec-file]` runs the full pipeline **end-to-end with
no human halts** — plan → RED test → implement → diff-review → draft PR. It reuses the four
existing subagents unchanged. The only human action is merging the resulting draft PR.

### What replaces the two human gates

In gated mode *you* answer the gates. In `auto` mode independent agents + objective CI answer them —
never self-approval (the maker never grades its own homework, which is what inflates confident-wrong fixes):

| Replaces | Mechanism | Model · effort | Directive (one line) |
|----------|-----------|----------------|----------------------|
| *both gates — objective* | **CI veto** — GitHub Actions run, or the in-tree suite as fallback | — *(no model)* | Runs FIRST; a red build/suite fails the gate **before a single reviewer token is spent** — the one gate the model can't argue past. |
| **Gate 1 — plan** *(was: human grill + approve)* | criteria-coverage check + **one `plan-reviewer`** (every tier) | **opus · high** (critical: **xhigh**) | Refute the plan — find why it fails or misses an acceptance criterion; default to reject if uncertain; fix inline. |
| **Gate 2 — diff** *(was: human review)* | **tier-sized blind `reviewer` panel** — 1 / 2 / 3 by difficulty, run in parallel | **sonnet · high** (trivial/normal) · **opus · high** (hard/critical) \* | Each judges ONE lens — *correctness* · *regressions+security* · *plan-match* — from the diff + plan only, **blind** to `audit.md` and to each other; refute, default reject. |
| **Gate 2 — arbiter** | **one `reviewer` as the arbiter** — runs on every split AND every unanimous *ship* (final sign-off); skipped only on a unanimous refute | **opus · high** (hard/critical: **xhigh**) | Resolve contested findings **on merit, not headcount** (a lone correct reviewer beats two wrong ones); on a clean ship, re-review independently rather than rubber-stamp. Justify the call in a required `## Options considered` (+/−) table. |

\* Panel model is **tiered**: trivial/normal panels take a **sonnet** override as a cost optimization
(a one-line fix doesn't pay for opus reviewers); hard/critical panels run on the reviewer default
**opus · high**, where a missed bug has real blast radius. Every panelist runs at the `reviewer`
frontmatter default `high`, one rung under the hard/critical arbiter; if no per-agent override is
available, all panelists run at opus · high. The arbiter runs at **opus · high** on trivial/normal and
**opus · xhigh** on hard/critical, and backstops every panel that doesn't unanimously refute.

Two non-gate mechanisms make those verdicts trustworthy: the **RED test** (frozen, must fail on a
real assertion — *red-for-right-reason*) and the **test-tamper guard** (content-hash check at the diff
gate). They are the executable ground truth the panel reasons against.

- **Non-halting:** never prints a GATE line; never waits for you. Terminal states are SHIP (draft PR
  opened, `stage: done`) or abort (`stage: aborted` with a structured report in `feature-research/<task-id>/report.md`).
- **Draft PR only; its own branch is the sandbox.** Auto-merge is never performed and it never pushes
  to the default branch. Within its own `anderson/auto/*` branch it may push, update the PR
  description, and **squash its commits into one clean commit** for tidy releases (force-push with
  `--force-with-lease` is allowed *only* on its own branch).
- **Baseline-green precondition.** If the test suite is red before any change, the run aborts.
- **Test-tamper guard.** The RED test is content-hash frozen at step 5; a mismatch at the diff gate aborts.
- **Bypass policy (operator override).** auto pushes through the SOFT guardrails to finish the task:
  low planner confidence, scope / runaway caps, and sensitive non-migration paths (`.github/`, CI
  config, lockfiles, dependency manifests) no longer abort — they attach a `needs-human` heads-up
  label instead. **Two hard rules never bend:** it **never authors or applies a migration** (hard
  stop + hand-off) and **never force-pushes any branch but its own** without consent. The verification
  engine — RED test, CI veto, blind panel, arbiter, tamper guard — is unchanged. See the AUTO-MODE
  OVERRIDE POLICY block in `commands/auto.md`.
- **Thrash breaker + replan bounce.** If findings don't shrink (or recur) across rework rounds, the
  run bounces back to PLAN **once** for a different approach, then escalates to `needs-human`.
- **Difficulty routing (step 3b).** A tier is computed from the plan's Scorecard (Risk / Coupling /
  Confidence / Testability) and re-computed against the actual diff size at the gate — it only ever
  escalates. The tier sizes everything downstream, so a one-line fix never pays for a 3-agent panel.
- **Plan gate (step 4).** Criteria-coverage check + **one** `plan-reviewer` on every tier (opus ·
  high, xhigh at critical — a rung above the opus · medium planner). Plan errors are cheap to fix, so the rigor budget is spent at the diff gate.
- **CI veto first (step 7c).** When the repo has GitHub Actions + a remote + `gh`, the branch is
  pushed and the run's conclusion is awaited; a red build fails the gate and **short-circuits before
  any reviewer tokens are spent**. Falls back to the in-tree suite when CI isn't available.
- **Tier-sized blind diff panel (step 7f).** 1 / 2 / 3 `reviewer`s by tier (correctness ·
  regressions+security · plan-match), run **in parallel** (each writes its own file + returns a
  verdict, so no shared-state collision), blind to `audit.md` and to each other. **Panel model is
  tiered:** trivial/normal panels run on **sonnet** (cost), hard/critical on **opus** (a missed bug
  there has real blast radius).
- **Arbiter always backstops the panel (step 7g).** One **opus** arbiter runs on every outcome except
  a unanimous refute: it resolves a split **on merit, not headcount**, and on a unanimous *ship* it
  runs as a final sign-off that independently re-reviews the diff rather than rubber-stamping.
  It must justify its call in a required `## Options considered` (+/−) table. Only a unanimous refute
  skips it (nothing to debate → straight to rework).
- **Red-for-right-reason (step 5).** The RED test must fail on an *assertion*; an import/syntax/
  collection error (a hollow red) triggers one bounded rewrite, then aborts.
- **Calibration metrics.** Every run emits a one-line `metrics:` record — `tier · panel_model ·
  reviewers · arbiter · arbiter_trigger · rounds · ci · replan · red · override · outcome` — to the PR
  + report, so each new behavior is greppable (which model the panel ran on, why the arbiter fired,
  which soft guardrails were relaxed) and the thresholds can be tuned from real outcomes.
- **PR body is the plan minus the how.** The draft PR opens with the source-ticket link (from the
  TaskSpec `source_url`, when present), What & why, the acceptance-criteria table with its Evidence
  column filled, the design, and a reviewer-facing how-to-test + config; scorecard / blast radius /
  error handling collapse below, then the audit trail and metrics. The 🛠 How is left to the diff
  (Open-questions print only when non-empty).
- **Multi-repo.** When the task must change other repos (TaskSpec `repos:`, scope spilling outside the
  repo, or a sibling repo in project memory / `CLAUDE.md`), each repo gets an isolated **git worktree**,
  its own branch, and its own cross-linked draft PR (labeled `needs-human`). A dirty tree is isolated
  in a worktree rather than aborting. The value of a cross-repo feature lives in the **seam**, so the
  shared contract (endpoint shape, event/message schema, shared type, CLI/env interface) is a
  **mandatory `contract` acceptance criterion** proven against a frozen fixture both repos pin — an
  isolated per-repo test can't catch a contract mismatch (both suites pass green while the feature is
  dead). The primary PR carries a **⚠️ Merge order** line and each companion links its `Blocked by`,
  so the contract-defining repo merges before its consumer.

Still review the PR carefully — auto mode is experimental, and the gates are orchestrator
*instructions* the model follows, not enforced code.

The scheduler hook (`hooks/scheduler.py`) exits silently when it detects `mode: auto` in the active
`state.md`, so hook chaining does not interfere with the command's own in-turn sequencing.

Living spec: `plugins/anderson/docs/auto-mode.md`. Design context: `plugins/anderson/docs/auto-mode-handoff.md`.

## 30-second quickstart

```
/plugin marketplace add amj-lang/anderson
/plugin install anderson@dodge-this
# restart Claude Code fully (not just /reload), then:
/anderson:start brief-views "normalize briefs_table.views[] into brief_views_table"
```

## What a real run looks like

![anderson — digital-rain intro](https://raw.githubusercontent.com/amj-lang/anderson/media/assets/anderson-demo.gif)

The fleet terminal boots into the same rain:

![fleet — Loading anderson…](https://raw.githubusercontent.com/amj-lang/anderson/media/assets/fleet-loading.png)

## Personas

| Persona          | Stage         | Role                                   | Model / effort |
|------------------|---------------|----------------------------------------|----------------|
| THE ARCHITECT    | `plan`        | writes the plan                        | opus / medium  |
| THE INTERROGATOR | `grill`       | you — triaged, graded Q&A (🔴🟡🟢)     | — (human)      |
| THE ORACLE       | `plan_review` | edits the plan inline + appends review to `## 🔭 Review` | opus / high\* |
| NEO              | `implement`   | executes the approved plan             | sonnet / medium|
| TRINITY          | `repair`      | root-causes a red suite (only when red)| opus / high    |
| AGENT SMITH      | `diff_review` | read-only diff review                  | opus / high\*  |
| SERAPH           | `diff_review` | security lens seat, summoned by the diff | opus / high  |
| NIOBE            | `diff_review` | performance lens seat, summoned by the diff | opus / medium (high from HARD) |
| THE MEROVINGIAN  | `diff_review` | dead-code lens seat: what this diff orphaned | opus / medium (high from HARD) |
| THE ONE          | `done`        | shipped — commit + PR                  | — (terminal)   |

SERAPH, NIOBE and THE MEROVINGIAN are not agents of their own: each is the `reviewer` agent in a
lens seat. `bin/crew.py` summons them from what the diff touches (paths and changed lines, no
model call): SERAPH for auth, sessions, API routes, input parsing, SQL/shell/HTML building,
secrets, dependencies, and always from HARD up; NIOBE for queries, loops over I/O, React effects,
caching; THE MEROVINGIAN whenever the diff changes or removes existing code. They review blind
into their own files first, then AGENT SMITH (or the auto arbiter) rules on their findings.

## Pipeline

```
plan ─▶ grill ─▶ plan_review ──[ YOU ]──▶ implement ──▶ diff_review ──[ YOU ]──▶ done
medium [ YOU ]   high* (edits)            medium        high* (read-only)
                                    ▲              │ fix_first
                                    └──────────────┘
```

| Stage        | Agent          | Model  | Effort | Gate  | Does                                  |
|--------------|----------------|--------|--------|-------|---------------------------------------|
| plan         | `planner`      | opus   | medium | —     | writes `plan.md` + blast radius + scorecard |
| grill        | *(you)*        | —      | —      | human | triages questions from the plan's own decision tree + ✅ criteria (`derived` rows are 🔴) + 💥 blast radius + 🧯 error rows, grades 🔴 ARCH/🟡 BEHAVIOR/🟢 PREF, prints a one-line manifest, asks 🔴→🟡 as 3-line cards (`🔴 n/N ▰▰▱▱…` + question + recommendation) with an adaptive progress bar, batches 🟢; folds decisions into `plan.md` — no subagent |
| plan_review  | `plan-reviewer`| opus   | high\* | human | **edits** `plan.md` inline + appends review to `## 🔭 Review`; re-scores + checks blast radius; verdict `ship`/`fix_first`/`regrill` |
| implement    | `implementer`  | sonnet | medium | —     | writes `audit.md`; ONE try at a failing test, then hands off |
| repair       | `test-fixer`   | opus   | high   | —     | only when tests are red: root-causes the failure, writes `repair.md` — never tiered |
| diff_review  | `reviewer`     | opus   | high\* | human | diff review appended to `plan.md` `## 🔭 Review` |

\* Review effort is not fixed: both critiques are sized by the **tier** computed from the plan's
Scorecard (plan-review/diff-review: trivial and normal → high/high; hard → high/xhigh; critical →
xhigh/xhigh — see [docs/tiering.md](docs/tiering.md)). The plan critique always runs a rung above
the opus/medium planner.

The tier and the crew it summons are printed, never implicit: a `**Tier:** <TIER> — plan_review
<model>/<effort> · implement sonnet/medium · diff_review <model>/<effort>` line sits under
`## 📈 Scorecard` in `plan.md`, and the same line is echoed on the Gate 1 card. The re-tier at the
diff gate rewrites both (with `was <old>` when it escalated), so you always see the bill before you
approve it.

The agents are **self-contained** — the implementer/reviewer logic is inlined, so
there is no external skill to install. Per-stage `model` + `effort` switch
automatically as the pipeline routes to each agent. Both human gates halt
unconditionally, even on a `ship` verdict.

Agent docs are written to concise 🎯/🛠/✅-style templates.

## The three modes

Same four subagents, same rework loop — three ways to drive them. The only thing that changes is
**who answers the gates**.

| Mode | Entry | Gates | Who decides | Terminal | Use when |
|------|-------|-------|-------------|----------|----------|
| **Gated / interactive** (default) | `/anderson:start` | 🛑 2 human halts | **you** (grill + 2 approvals) | PR (you ship via `:approve-diff`) | you want eyes on the plan and the diff before anything merges |
| **Autonomous / `auto`** (experimental) | `/anderson:auto` | none — never halts | **panels + CI** (objective ground truth) | **draft PR** or abort + `report.md` | bulk / unattended fixes you'll review at the PR |
| **Headless / CI** | `bin/feature.sh` | `exit`s at each gate (codes 10/20) | **your CI / Makefile** | PR on `--approve-diff` | scripting, CI, walk-away |

**Gated / interactive** — `plan → grill → plan_review →` 🛑 **Gate 1** `→ implement → diff_review →`
🛑 **Gate 2** `→ ship`. Both halts are unconditional, even on a `ship` verdict (green ≠ understood).
Drive the gates with `/anderson:approve-plan`, `:approve-diff`, `:rework`, or plain text. A
between-gate scheduler (`hooks/`) can auto-chain the non-gate transitions for you — see *Optional —
autonomous between-gate chaining* below.

**Autonomous / `auto`** — `plan → plan-gate → RED test → implement → diff-gate → draft PR`, no human
in the loop. The human gates are replaced by a **CI veto** (a red build short-circuits before any
reviewer tokens) + a **tier-sized blind reviewer panel** + an **arbiter on split**. A difficulty
*tier* (trivial/normal/hard/critical) sizes the whole harness, so a one-line fix doesn't pay for a
3-agent panel. Under the **operator override policy** it pushes through soft guardrails to finish the
task; two hard rules never bend — **never authors a migration**, **never force-pushes outside its own
branch**. Always opens a **draft PR** (never auto-merges). See *auto mode (experimental)* at the top.

**Headless / CI** — the deterministic `bin/feature.sh`; same pipeline, exits at each gate so it
composes with CI or a Makefile, and `--approve-diff` ships for real. See *Use it — headless* below.

## Structure (important)

This repo is a **marketplace root** with the plugin in a subdirectory — the only
layout the CLI's marketplace loader handles reliably. Do NOT collapse these:

```
anderson/                       <- add THIS path/repo as the marketplace
├── .claude-plugin/
│   └── marketplace.json           <- source: ./plugins/anderson
└── plugins/
    └── anderson/               <- the plugin itself
        ├── .claude-plugin/plugin.json
        ├── agents/  commands/  hooks/  bin/  README.md
```

## Install — for yourself (covers all your repos)

**From a git remote (recommended).** The repo lives at `amj-lang/anderson`, so you
and teammates run the same two lines:

```
/plugin marketplace add amj-lang/anderson
/plugin install anderson@dodge-this
```

**Local marketplace (alternative — no git remote needed).** Point Claude Code at the
**marketplace root** — the dir that contains `.claude-plugin/marketplace.json`
(this repo's top level), substituting your real absolute path:

```
/plugin marketplace add /absolute/path/to/anderson
/plugin install anderson@dodge-this
```

Installed plugins live in `~/.claude/plugins/`, so the agents and the
`/anderson:*` commands are available in **every** repo you open — nothing
per-project. Restart Claude Code fully (not just `/reload`) after installing.

### If it doesn't appear in the list

1. Confirm you added the **marketplace root**, not `plugins/anderson` and not
   the `.claude-plugin` folder. The path must directly contain
   `.claude-plugin/marketplace.json`.
2. Remove and re-add, then fully restart Claude Code (not just /reload):
   `/plugin marketplace remove dodge-this` → `/plugin marketplace add <path>`.
3. Check the cache landed: `~/.claude/plugins/known_marketplaces.json` lists
   `dodge-this`, and `~/.claude/plugins/marketplaces/dodge-this/plugins/anderson/`
   contains the files.
4. Then `/plugin install anderson@dodge-this` and restart once more.

### Recommended companion plugins

Every agent already lists these tools; they light up once the plugin is installed:

```
claude plugin install typescript-lsp@claude-plugins-official   # + npm i -g typescript-language-server typescript
claude plugin install context7@claude-plugins-official         # current library docs (hosted MCP)
```

LSP gives exact reference tracing (blast radius, THE MEROVINGIAN); context7 gives the planner,
plan-reviewer, implementer and test-fixer current library docs instead of memory. Without them
the agents fall back to Grep and the installed types.

## Install — for your team

Push the repo somewhere they can read it, then each teammate runs the same two
lines:

```
/plugin marketplace add amj-lang/anderson
/plugin install anderson@dodge-this
```

Check the repo into version control so the team improves it together. See
**Updating to a new version** below for the bump + reinstall flow.

### Updating to a new version

Bump `version` in **both** `plugins/anderson/.claude-plugin/plugin.json` and the
root `.claude-plugin/marketplace.json` (keep them in sync), then:

```
/plugin marketplace update dodge-this      # re-reads the source (local dir or remote)
/plugin install anderson@dodge-this     # pulls the new version
```

then restart fully. If it doesn't take, `/plugin marketplace remove dodge-this` →
`/plugin marketplace add <path-or-repo>` and restart once more.

## Use it — interactive (slash commands, zero setup)

| Command | What it does | What to expect |
|---------|--------------|----------------|
| `/anderson:start <slug> <goal>` | **Entry point** (gated mode). Normalizes any ticket/design reference into scratch (intake), seeds `state.md`, plans, **grills you** one question at a time, then plan-reviews (edits the plan inline). | Halts at 🛑 **Gate 1** on a TL;DR card (what · criteria · scorecard · verdict); open `plan.md` when a line raises doubt. |
| `/anderson:approve-plan <slug>` | Pass **Gate 1**: implement + independent diff-review. | Code + `audit.md` written, review appended. Halts at 🛑 **Gate 2**. Read `## 🔭 Review` AND the diff. |
| `/anderson:approve-diff <slug>` | Pass **Gate 2** = **SHIP for real**: branch `anderson/<slug>` + commit + push + open PR (all guarded), then clean scratch. | Branch + PR URL, or a local-commit fallback if no remote/`gh`. **Never force-pushes.** |
| `/anderson:rework <slug>` | Diff review said `fix_first` — loop the implementer on the "Still open" blockers only, then re-review. | Back to 🛑 **Gate 2**. Bounded by `max_iterations`. |
| `/anderson:status <slug>` | Dashboard / sanity check. | Current stage, next agent + model/effort, both verdicts, iteration vs max, and the `CLAUDE_CODE_SUBAGENT_MODEL` override check. Read-only. |
| `/anderson:demo` | Zero-token dry-run of the whole pipeline. | All stage banners + both gate lines + ship banner. No agents, no files, no tokens. |
| `/anderson:auto <id> <title> [body\|@file]` | **Autonomous mode** — no gates: plan → plan-gate → RED test → implement → CI-veto + panel diff-gate → **draft PR**. | Terminal SHIP (draft PR) or abort + `report.md`. Review the PR — auto mode is experimental. |
| `/anderson:help` | Static quick-reference card: every command, arguments, gates, tiers. | One printed card. Reads nothing, no agents, no state — for the live dashboard use `:status`. |
| `/anderson:fleet` | Installs the **`fleet`** terminal command (THE OPERATOR: every Claude session on the machine, persona, stage, `$`, ctx; ⏎ jacks into its tmux pane) and prints the launch card. | `~/.local/bin/fleet` written (idempotent, survives plugin updates) + the card. No agents. Then `fleet` in any terminal — see [Extras](#extras-terminal). |

All commands are **namespaced** `/anderson:<command>` — `/anderson:start`,
`/anderson:approve-plan`, `:approve-diff`, `:rework`, `:status`. Bare plugin-name
invocation (`/anderson` alone) does **not** resolve — Claude Code namespaces plugin
commands — so the start command is `/anderson:start`. None of these are mandatory
anyway: once a flow is running you can drive every gate in plain text —
"approved, go" / "ship it" / "rework the blockers" — since the agents read the
same `state.md`.

**What you see while it runs.** Each stage prints a compact framed banner — stage,
persona, and model on one line; a quote picked deterministically per stage on the next:

```
╭─ ⌐■-■  IMPLEMENT · 4/5 · NEO · sonnet/medium
│  "touch only what the plan told you to touch"
╰─
```

The agents are also colour-coded in the subagent panel (planner=blue,
plan-reviewer=purple, implementer=green, test-fixer=red, reviewer=orange), so you can tell at a
glance which one is working.

State persists in `feature-research/<task>/state.md` in the current repo, so you
can stop at a gate and resume later.

### State file

`state.md` is a machine-only file — it is not a human-facing artifact. Humans read `plan.md`.

The machine-read contract shared by `hooks/scheduler.py`, `commands/status.md`, and
`bin/feature.sh`. Seeded by `/anderson:start` with this exact block (parsing is lenient —
tolerates `- ` bullets and `**` bold around keys):

```
<!-- STATE:START -->
task:            <task>
stage:           plan
gate:            none
iteration:       0
max_iterations:  2
exit_rule:       all tests pass and lint clean, only major issues fixed
plan_verdict:    pending
diff_verdict:    pending
<!-- STATE:END -->
```

Fields: `task` = slug; `stage` = current pipeline stage; `gate` = `none` or `human`;
`iteration` = rework pass count; `max_iterations` = hard cap on implement↔review loops;
`exit_rule` = the human-readable rule the diff reviewer enforces; `plan_verdict` /
`diff_verdict` = `pending`, `ship`, `fix_first`, or `regrill`.

`plan.md` reads human-first: **What → Why → ⚠️ Behavior change → 🗺 Design → ✅ Acceptance criteria → How → 📈 Scorecard** stay
visible (hard budgets: What ≤ 3 lines, ⚠️ Behavior change ≤ 2 lines, one line per How bullet); the bodies of 🗺 Design,
💥 Blast radius, 🧯 Error handling, and ✅ Decisions sit inside `<details>` collapses. The
**`## ✅ Acceptance criteria`** table (`# | Criterion | Source | Proof | Evidence`) is the plan's
spine: criteria come from the ticket (verbatim), the design inventory (exact strings — a
`/anderson:start` intake step normalizes Figma URLs / ticket screenshots / image files into
`feature-research/<task>/design/` + an `inventory.md`), or planner judgement (`derived` — the
grill confirms those as 🔴 questions). Each criterion names a proof type — `test` (must fail
without the change), `visual` (screenshot of the running UI vs the design, compared by the diff
reviewer), `e2e` (ephemeral script in scratch — gate-time only, deleted at ship, `promote
candidate` when worth keeping), or `manual` (only when nothing executable can cover it). The
implementer fills the Evidence column; the diff reviewer's criteria-evidence lens blocks on a
blank cell, a test that passes without the diff, or a visual mismatch. Both gates halt on a
TL;DR card (what · criteria/proof counts · scorecard · verdict), so the plan file only needs
opening when a line raises doubt.

`plan.md` carries further mandatory sections beyond the How narrative: a **`## 💥 Blast radius`** table (planner traces all dependents/callers/siblings/tests/docs before finalizing; reviewer hard-checks it, blocking on blank cells or missed in-scope sites), a **`## 🧯 Error handling`** table (each failure path the change touches, classed `deduced` = handle now or `needs-context` = a business call mirrored into `## ✅ Decisions`; reviewer blocks on a missing path, the diff-review correctness lens checks each `deduced` row is handled), a **`## 📈 Scorecard`** (6 dimensions — Risk, Horizontality, Testability, Reversibility, Confidence, Coupling — with Planner and Reviewer columns in one table; gaps ≥ 3 reconciled inline; Risk ≥ 8 or Confidence ≤ 3 blocks `ship`), and a **`## 🔭 Review`** section (last, reserved — the plan-reviewer appends its structured report here after making inline edits, and the diff-reviewer appends its diff review here; replaces the former separate `diff-review.md` and `## Diverged because` block). The scorecard is echoed verbatim into `audit.md` by the implementer.

## Models & effort — what runs where, and how to verify

Each agent declares its own `model` + `effort` in frontmatter, and these switch
automatically per stage (planner opus/medium, plan-reviewer opus/high, implementer
sonnet/medium, test-fixer opus/high, reviewer opus/high; the tier raises review effort to xhigh by switching to the `plan-reviewer-xhigh` /
`reviewer-xhigh` twins, since effort is frontmatter-only and the Agent tool has no per-call effort). Resolution order is: `CLAUDE_CODE_SUBAGENT_MODEL`
env var → per-invocation override → **agent frontmatter** → main session. The rank of
the first two against each other is unverified — if you set the env var, the transcript
grep below is ground truth for what actually ran.
`model:` in agent frontmatter is a floating tier alias — `opus` resolved to
`claude-opus-5` the day Opus 5 shipped, with no edit here — so a model release
needs no anderson change; the plugin pins no dated ID.

**No Fable, no model flag.** Every critique stage — plan-review and diff-review (panel +
arbiter) — runs on **Opus** (`model: opus` in the `reviewer` / `plan-reviewer` frontmatter). Opus
5.5 beats Fable 5.1 on every published benchmark at a fraction of the per-token price
([docs/tiering.md](docs/tiering.md)), so the old `--opus` flag and the `review_model` state field
are gone; the tier alone sizes review effort. In auto mode the TRIVIAL/NORMAL panel stays on
sonnet (`panel_model` metric reads `sonnet` or `opus`).

**Set your own models permanently.** Set `env` in `~/.claude/settings.json`
(user-wide) or `.claude/settings.json` (project) to pin every stage to one
model for all future runs:

```json
{
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet",
    "ANTHROPIC_MODEL": "sonnet"
  }
}
```

`CLAUDE_CODE_SUBAGENT_MODEL` covers every subagent, `ANTHROPIC_MODEL` the main
thread. Consequence: with it set, every stage runs on that one model, so
per-stage tiering flattens. `/anderson:status` reports the override for you;
or check directly what's actually running:

```
echo "${CLAUDE_CODE_SUBAGENT_MODEL:-<unset>}"
```

**What to start the main session as.** The main thread here is only an
orchestrator (reads state, dispatches, prints banners) — it does no heavy
thinking, so run it cheap: `claude --model sonnet`. The subagents override it from
frontmatter regardless. Bonus: keeping main on a *different* model than a given
agent makes a failed switch obvious.

**How to confirm the switch actually happened** (after a run): subagent
transcripts log the model used, at `~/.claude/projects/<proj>/<session>/subagents/agent-<id>.jsonl`.

```
grep -rho 'claude-[a-z0-9.-]*' ~/.claude/projects/*/*/subagents/ | sort | uniq -c
```

You should see opus IDs for planner/reviewers and a sonnet ID for the implementer.
The `/agents` Running tab also shows each live subagent and its colour. (Effort
isn't always surfaced in the UI; the frontmatter sets it and it overrides the
session level while the agent is active — trust the declared value, or inspect the
transcript if your build logs it.)

## Use it — headless (CI / walk-away)

`bin/feature.sh` is the deterministic version: it `exit`s at each gate (codes 10
/ 20) so it composes with CI or a Makefile, and on `--approve-diff` it **ships for
real** — branch + commit + push + open PR, guarded exactly like the interactive
command (it builds the message deterministically from the scratch instead of asking a
model; needs `git` + `gh` auth in CI, and degrades gracefully without them). Add it to
PATH or call directly:

```
./bin/feature.sh start brief-views "normalize views[] into brief_views_table"
./bin/feature.sh --approve-plan brief-views
./bin/feature.sh --approve-diff brief-views   # ship: branch + commit + push + PR (guarded);  or --rework
```

## Optional — autonomous between-gate chaining

`hooks/hooks.json` registers a `SubagentStop`/`Stop` scheduler that auto-advances
the state and chains plan→grill→plan_review and implement→diff_review without you
issuing each command, still halting at the **grill** checkpoint (an interactive,
human step — no subagent) and the two approval gates. It's on by default in
the plugin; remove the `hooks/` directory if you'd rather drive every step
explicitly.

If plan-review returns `regrill`, the scheduler routes back to the **grill** step (human-gated) for another pass rather than halting at the plan gate.

The scheduler emits hook JSON on stdout to drive the next turn:

- **Chain forward** (gate=none transitions): `{"decision": "block", "reason": "<directive>"}` —
  this prevents the Stop and feeds `reason` back to the model as its next instruction,
  making chaining real rather than advisory. Valid for both `Stop` and `SubagentStop`.
- **Human-gate / max_iterations notice**: `{"hookSpecificOutput": {"hookEventName": "<Stop|SubagentStop>", "additionalContext": "<notice>"}}` —
  surfaces the notice without forcing another turn, allowing the Stop.
- Stage is advanced on disk **before** emitting, so re-firing the hook never re-blocks
  the same step. A re-entrancy guard (`stop_hook_active`) ensures silent exit if
  Claude Code signals the hook is being called during a hook-induced stop.

## Exit conditions

In each task's `state.md`: `max_iterations` (hard stop on implement↔review loops)
and `exit_rule` (the human-readable rule the diff review enforces). Set them
before a rework-heavy run; the loop stops and escalates rather than looping
forever. (There's no `budget_usd` — on a subscription nothing meters per-token
spend, so a USD cap can't be enforced; cap spend at your API key's billing limit
if you ever run this metered.)

## What happens after ship

The durable record is your **git history + the PR**, not the scratch files. On
`/anderson:approve-diff` the loop now **ships for real**, in this order:

1. Builds the commit subject (`<goal> (review: ship · N blocking resolved)`) and a
   PR body (the plan minus the how: what & why, criteria + evidence, design, how-to-test
   + config, and scorecard / blast radius / error handling collapses) from the scratch —
   *before* it deletes anything.
2. **Branches if needed:** if you're on the default branch (`main`/`master`) it
   creates and switches to `anderson/<slug>`; if you're already on a feature branch it
   commits there. It never commits straight to the default branch and never force-pushes.
3. **Commits** the work under your own git identity (no Claude trailer), staging only
   real code — the scratch dir is gitignored, so it's never committed.
4. **Pushes + opens the PR** via `gh`, *guarded*: if there's no remote, no `gh`, or
   you're not authed, it degrades gracefully — commits locally and prints the PR body
   for you to open by hand. The ship never fails on a missing tool.
5. **Removes `feature-research/<task>/`** last. Nothing stale is left behind.

So in a fully-wired repo, one gate approval = clean branch + commit + PR. In a bare
repo it still does as much as it safely can and hands you the rest.

## Token notes

Each agent runs in its own context window and gets only its own prompt — verbose
work stays out of your main context. State lives on disk, so per-iteration context
stays flat. Keep agent prompts byte-stable so Claude Code caches the prefix (cache
reads ≈ 0.1× input); don't inject the date/iteration into a prompt prefix — that's
what the on-disk state is for.

The read-heavy review agents are scoped to the plan plus the files it names
(diff-first) instead of sweeping the tree, which trims input tokens — a modest,
input-side saving, not a dramatic one.

## Extras (terminal)

![fleet — THE OPERATOR: every Claude Code session on one screen](https://raw.githubusercontent.com/amj-lang/anderson/media/assets/fleet-operator.png)

Optional flourishes in `bin/` — run them in a real terminal (the in-loop banners are plain text and don't animate):

- **`fleet`** — **THE OPERATOR**, the cross-repo fleet monitor and, since phase 2, where work
  starts. Install once with `/anderson:fleet` (writes a `fleet` shim to `~/.local/bin` that
  resolves the newest installed anderson at run time, so plugin updates never break it), then in
  any terminal: `fleet` (outside tmux: attaches a per-workspace tmux session, status bar on; inside
  tmux: runs right here), `fleet --here` (right here regardless), `fleet --tmux` (the legacy single
  session named `fleet`, status bar hidden), `fleet --pane` (45% side pane inside tmux), `fleet
  --window`. The installer also prints an optional `prefix+F` tmux hotkey line.

  Rows are the repos of the workspace fleet was launched from (one nested level): a repo is a row,
  a dir holding several repos is a collapsible group row, live sessions nest under their repo, and
  sessions from elsewhere land in an `elsewhere` group. No repos found under the launch dir falls
  back to today's flat session list. Each row: repo · anderson task · **persona on the job**
  (▲ ARCHITECT, ◇ INTERROGATOR, ◎ ORACLE, ● NEO, ✚ TRINITY, ▣ AGENT SMITH, ★ THE ONE, ○ T. ANDERSON = no
  pipeline yet) · stage `n/max` · **tier** (how hard the pipeline decided the task is: `triv` ·
  `normal` · `HARD` · `CRITICAL`, from state.md) · model · **now** (`▶ Bash pytest -q`, `▶ Agent implementer`,
  `☎ ring` = waits on you, `☎ permission Bash`, `✝ sentinel` = process gone, `⟲` = rework loop) ·
  $ · context bar · age. Detail pane: verdicts, lines ±, tmux pane, last words, a mood-matched line
  from `quotes.txt`. Runs **outside** Claude (python stdlib curses, zero tokens) in its own tmux
  session; rows ring first.

  Rows are numbered; sessions with no pipeline show their first prompt as a quoted title; ringing
  rows say for how long (`☎ ring 12m`); the ctx cell turns red past 80%.

  Keys: `↑↓` tune · `1`..`9` / `⏎` **jack in** on a session row (switches tmux to that session's
  pane; without tmux, on macOS it focuses the iTerm2 / Terminal.app tab that owns the session, or
  brings the owning IDE forward for integrated terminals, so tmux is optional: `fleet install
  --with-tmux` adds it via brew / apt / dnf if you want panes) — or **spawn an agent** on a
  repo/group row: `⏎` opens a prompt box, then `p`/`a`/`A` launches a claude agent (bare /
  `/anderson:start` / `/anderson:auto`) into that repo — or the workspace root, on a group — in a
  terminal of its own, so the monitor keeps the window it is in. Drilled into a repo that has no agents
in it there is no row to select, and `⏎` spawns into that repo anyway. If that repo is already parked on a
  feature branch, the agent does not land in it: it gets a worktree (`.worktrees/<task>` on branch
  `anderson/<task>`, cut from the default branch), and its row still nests under the repo. `J`/`K` reorder a repo/group among its siblings, `space` (`←`/`→` too)
  collapses/expands it; both persist per workspace. `D` pops a session's tmux window out into its
  own OS terminal window. `w` white rabbit
  (oldest ring, expanding any collapsed group in the way) · `r` kill (asks first; the row is hidden with it) · `R` rebase that checkout's branch onto main/master and force-push it (asks first) — the only force push fleet does, `--force-with-lease` on that one branch, refused outright when the base branch is not protected on GitHub, when the tree is dirty, or on main itself; conflicts abort it and stay yours · `b` hide the row (any row, the process is left alone) or, on a repo/group row, that whole repo and its agents (saved per workspace) · `h` show hidden rows and repos (`b` on one un-hides) · `c` copy the
  `claude --resume` command for that session · `n` desktop notification on ring · `m` sound · `s` next ring sound · `/` filter ·
  `t` theme · `p` wording · `?` manual · `q`.

### What fleet needs

Required: **python3** (stdlib only, no pip) and the tools every macOS / Linux box already has (`ps`, `lsof`,
`less`; `afplay` / `osascript` on macOS). Everything else is optional and `fleet install` tells you what is
missing; `fleet install --extras` installs the first two, `--with-tmux` the third:

| tool | for | install |
|---|---|---|
| `glow` | `o` renders plan.md / audit.md as real markdown (else `less` with a light colouring) | `brew install glow` · `dnf install glow` · apt: [charm repo](https://github.com/charmbracelet/glow#installation) |
| `terminal-notifier` | macOS desktop banners (`n`): reliable, listed in System Settings, click focuses fleet | `brew install terminal-notifier` |
| `tmux` | `fleet --pane` / `--window` / `--tmux`, and ⏎ jack-in by pane | `brew install tmux` · `apt install tmux` · `dnf install tmux` |
| `notify-send`, `paplay`/`aplay`, `xdg-open` | Linux: banners, ring sound, `O` open | usually there (`libnotify`, PulseAudio / ALSA) |

`/anderson:fleet --extras` and `/anderson:fleet --with-tmux` pass the flags through.

### Keeping fleet current

`fleet update` refreshes the marketplace, updates the anderson plugin through the `claude` CLI, and
prints what it moved from and to; restart Claude Code to apply it. The `~/.local/bin` shim resolves the
newest cached version every time it runs, so it never needs re-installing after an update. Without the
`claude` CLI on PATH, run `/plugin update anderson` from inside Claude Code instead.

  **Five themes**, cycled live with `t` or set with `--theme <name>`, remembered per user in
  `~/.claude/fleet/prefs.json` together with wording and motion:

  | theme | look | motion | winks |
  | --- | --- | --- | --- |
  | `matrix` | green phosphor | header rain tail, ringing rows breathe 1/s | full |
  | `construct` | white void | none | quotes and toasts off |
  | `zion` | amber machine level | slow spinner | full |
  | `nebuchadnezzar` | cold cyan/blue console | one heartbeat dot | full |
  | `agent` | monochrome, red alerts | none | Smith's adversary lines only |

  `p` (or `--plain`) swaps the header lingo (`zion · 3 jacked in · 1 ringing · 0 sentinels`) for
  plain English (`fleet · 3 live · 1 waiting · 0 dead`); `--calm` removes motion from any theme.
  `+` / `-` (or `--zoom 16`) grow the font while fleet runs and restore it on quit: Terminal.app
  only, since it is the one terminal with a font-size API; iTerm2 and IDE terminals use ⌘+ / ⌘-.
  The boot screen (0.7s of rain, then `Loading anderson…` and a line that rotates every launch) is
  skipped with `--no-intro`. `--demo` adds four fake rows, `--once` prints one plain frame,
  `--ascii` uses single-byte glyphs, `--selftest` proves every line equals the terminal width at
  40..300 columns in all five themes (wide/CJK/accents safe). Only the frame lines that changed are
  repainted, so an idle monitor emits nothing.

  Data, richest first, each optional (the view degrades, never breaks):
  1. **no setup**: `ps` + `lsof` find running `claude` processes; the transcript tail
     (`~/.claude/projects/<cwd>/<sid>.jsonl`) gives last tool / last words / context tokens; the
     repo's `feature-research/*/state.md` gives stage → persona.
  2. **this plugin's hooks** (`hooks/fleet_event.py` on SessionStart / UserPromptSubmit /
     PostToolUse / Notification / Stop / SessionEnd) write `~/.claude/fleet/<sid>.event.json`: the
     exact waiting-on-you vs working signal, permission prompts included.
  3. **statusline heartbeat** (`bin/heartbeat.py`) writes `~/.claude/fleet/<sid>.status.json`: `$`
     cost, precise context %, model, lines ±, tmux pane, and your subscription windows (the `/usage`
     5-hour / 7-day percentages and reset times, shown in the footer). `$` is Claude Code's own
     estimate at API list price: notional on a subscription, a gauge of which session burns most. `bin/statusline.sh` calls it; to keep your
     own statusline, wrap it:
     ```
     "statusLine": { "type": "command",
       "command": "bash /ABS/PATH/plugins/anderson/bin/fleet-statusline.sh bash /ABS/PATH/your-statusline.sh" }
     ```
  Sessions silent for 24h are forgotten; `b` forgets a sentinel now. `/anderson:fleet` prints the launch card.

- **`bash bin/matrix.sh`** — green digital-rain intro that resolves into the `⌐■-■ A N D E R S O N` logo. Honors `NO_COLOR` / non-TTY (prints a clean static frame). Tunables: `MATRIX_DELAY`, `MATRIX_FRAMES`. Great for a demo GIF.
- **`bin/statusline.sh`** — a one-line status bar with the live loop stage + a calm shimmer (glasses + rain cycle ~1/sec). Opt-in; add to `settings.json` with an absolute path (this replaces any existing statusline):
  ```
  "statusLine": { "type": "command", "command": "bash /ABS/PATH/plugins/anderson/bin/statusline.sh" }
  ```

## Install counting

The plugin counts how many machines run each version, and nothing else.

On the first session after an install or an update, a `SessionStart` hook fetches a one-byte `ping`
file attached to that version's GitHub release. GitHub publishes a public `download_count` for every
release asset, so the release *is* the counter: there is no server, no account, no analytics vendor,
and no payload. The request carries no identifier, no project path, no machine, OS or user
information. GitHub sees an IP address it already saw when the marketplace cloned the repo.

It fires once per version per machine. A marker at `~/.claude/anderson/counted` records which
versions have been counted, is written before the request goes out, and the request itself is
detached with a 5-second timeout, so a slow or offline network costs the session nothing.

To turn it off completely, set either variable in your shell profile:

```sh
export ANDERSON_NO_TELEMETRY=1   # or the cross-tool DO_NOT_TRACK=1
```

The counts are published in [`metrics/installs.json`](../../metrics/installs.json) on `main`, next to
the clone traffic in [`metrics/traffic.json`](../../metrics/traffic.json). The code is
[`hooks/ping.py`](hooks/ping.py) — about forty lines.

## Changelog

- **0.56.0** — **Sharper crew profiles; context7 reaches the builders.** SERAPH establishes the trust boundary first (from CLAUDE.md / SECURITY.md / README, or names its assumption), runs `npm audit` on dependency changes and `gitleaks` / `semgrep` when installed, and ignores fixture secrets. NIOBE decides hot versus cold paths with LSP `incomingCalls` and sizes new client dependencies. THE MEROVINGIAN greps a symbol's name as a string before calling it dead and treats convention-loaded files (framework routes, configs, stories, workers) as live. Every lens finding carries `severity · confidence`, and AGENT SMITH logs each seat's confirmed/raised tally so its hit rate is measurable. The planner reads `docs/adr/` and `CONTEXT.md`. Planner, plan-reviewer, implementer and test-fixer get the context7 docs tool (installed version's types first).

- **0.55.1** — **NIOBE and THE MEROVINGIAN move off Sonnet.** Performance and dead-code calls are judgment, not pattern matching: both seats now run opus/medium below HARD and opus/high from HARD up (SERAPH stays opus/high). Medium needs its own twin, `reviewer-medium`, since effort is frontmatter-only; `bin/crew.py` now names the agent per seat and the twin test covers all three twins.

- **0.55.0** — **The crew: SERAPH, NIOBE and THE MEROVINGIAN join the diff review; LSP reaches every agent; typecheck and lint are enforced.** Three lens seats of the `reviewer` agent (no new agent files), summoned by `bin/crew.py` from the diff's paths and changed lines: SERAPH (security, always from HARD up), NIOBE (performance), THE MEROVINGIAN (dead code this diff orphaned, traced with LSP `findReferences`). They review blind in parallel into their own files, then AGENT SMITH (gated) or the arbiter (auto) rules on their findings. The planner's blast radius gains a 'code this change makes dead' vector so deletions get planned. Every agent gets the `LSP` tool (exact reference tracing; Grep as fallback). The implementer runs the repo's typecheck and lint before finishing and the reviewer re-runs them: the 'lint clean' exit rule was never enforced. Auto mode: HARD now includes security/auth/concurrency changes (it had drifted from start mode), and the diff guard counts untracked new files.

- **0.54.0** — **Agent audit against Claude's prompt-audit guide; xhigh review seats are real.** Effort is frontmatter-only (the Agent tool has no per-call effort), so the tiered "effort override" never ran: CRITICAL plan review and HARD+ diff review ran at high. New `plan-reviewer-xhigh` / `reviewer-xhigh` twins (same body, `effort: xhigh`, kept identical by `test/test_agent_variants.py`) and the commands pick the agent by tier. Per agent: planner gets Edit + a rework pass (auto re-runs no longer wipe the review) and a split outlet for oversized tasks; the unread Observability score is gone. Plan-reviewer drops Bash/Write, judges the approach first, and its `fix_first`/`regrill` now match auto routing. Implementer learns the frozen test is hash-checked. Reviewer's panelist/arbiter seats stop contradicting its prompt, and test-fixer fixes outside the plan are now reviewed. Test-fixer treats a flake in touched code as a race. Fable 5.1-era prompt lines removed.

- **0.53.1** — **Root README explains the Opus 5.5 switch.** New "Why Opus 5.5" section: the
Opus 5.5 vs Fable 5.1 launch benchmark table, what moved per stage in 0.53.0, and the caveat.

- **0.53.0** — **Opus 5.5 takes every critique seat; Fable and `--opus` are gone.** Opus 5.5 beats
Fable 5.1 on every benchmark Anthropic published at launch (Terminal-Bench 4.0 66.4% vs 55.8%,
CursorBench 57.8% vs 51.8%, …) at 2.5× less per token, so the `reviewer` and `plan-reviewer` agents
now declare `model: opus`, and the `--opus` flag and `review_model` state field are removed (an old
state.md that still carries it is ignored). New effort table: planner **opus/medium**; plan-review
**opus/high** on every tier (trivial no longer skips it) and **xhigh** at critical, always a rung
above the planner; implementer sonnet/medium; repair opus/high; diff-review **opus/high**, **xhigh**
from hard up. Auto follows: plan gate as above, panel sonnet/high (trivial/normal) or opus/high
(hard/critical), arbiter opus/high or opus/xhigh. Statusline and fleet show the tier-sized effort.
`docs/tiering.md` rewritten with the per-step tables and the benchmark comparison.

- **0.52.1** — **Docs caught up with the last three changes.** The `repair` stage is now in the
places that describe the pipeline rather than only the changelog: the stage/agent table, the auto-mode
spec (step 6b, the CI-veto route, "a red suite is not a rework"), `docs/tiering.md` (repair is never
tiered — a red test is a diagnosis, not a matter of doubt), the agent colour legend and the models
section. Fleet's `R` (rebase + the one fenced force push) and ⏎-spawn-from-an-empty-repo are in the
key tables, not just the in-app manual.

- **0.52.0** — **TRINITY: a red suite is a diagnosis problem, not a typing problem.** The
implementer (sonnet/medium) used to own every red test, including the ones it had just failed to
fix — so it looped, and a loop on a test it never root-caused is how tests end up skipped,
loosened or quietly deleted. Now it gets exactly ONE try; a test still red after it goes to
TRINITY, a new `repair` stage running the **test-fixer** subagent on **opus/high** (always —
`--opus` and `review_model` do not reach it). TRINITY reproduces the failure, re-runs it once to
rule out a flake, names the root cause in one line before editing anything, fixes the cause in
production code, and proves both the single test and the FULL suite green. It may never weaken,
skip, `xfail`, retry, widen or delete a test — and the frozen test's tamper hash still guards the
gate. It writes `repair.md` with a verdict: `fixed` · `flake` · `replan` (the approach cannot pass
— bounce to the planner instead of patching) · `needs-human`. Budget: 2 rounds. In auto mode a CI
veto now routes here instead of to the rework loop, which is for review findings only. Sequential
by design: the fixer edits the tree the reviewers read, so it never runs beside the panel.

- **0.51.0** — **An empty repo is a starting point, not a dead end.** Drilling into a repo with no
agents left you on a screen with nothing to select, so `⏎` had no row to spawn from and the only way
forward was `←` back to the overview. Drilled in with no rows, `⏎` now opens the prompt box for that
repo itself (the target is rebuilt from the scan), and the empty screen says so.

- **0.50.0** — **`R`: rebase onto main, force-push one branch.** A branch that has been running for a
day drifts behind `main`, and catching it up by hand means leaving fleet. `R` on a repo, worktree or
session row rebases that checkout's branch onto the default branch and force-pushes it. It is the
only force push fleet performs anywhere, and it is fenced in: `--force-with-lease`, one explicit
`<branch>:refs/heads/<branch>` refspec, never the base and never another ref. It refuses before
touching anything when the checkout sits on `main`/`master` itself, when the tree is dirty, or when
GitHub does not report the base branch as protected — and an answer it cannot get (no `gh`, no GitHub
remote) counts as unprotected, because an unprotected base is what makes a mis-aimed force push
unrecoverable. Conflicts are never resolved for you: the rebase is aborted, nothing is pushed, and
the message hands the job back.

- **0.49.0** — **fleet sees three levels, and worktrees.** Two ways a repo could sit in your
workspace and never get a row. Repos one level deeper than the scan reached
(`workspace/autoretouch/mpe/watermark`) were dropped with the plain dir holding them: they now
flatten into the group as `mpe/watermark`, so the tree still stays two deep. And a checkout whose
`.git` is a *file* rather than a directory — every `git worktree add` and every submodule — failed
the repo test everywhere it was made, so it vanished from the scan *and* sent `workspace_root()`
walking past it to the wrong workspace. `.git` now counts either way.

- **0.48.2** — **One session, one task dir.** The other half of the duplicate-task report: starting
the same work twice under a slightly different slug (`ais-showcase-poses` first, then
`ar-2168-ais-showcase-poses` once the ticket turned up) left two task dirs in the repo, and fleet —
which falls back to the newest state.md — then put both agents on the same task. `feature.sh seed`
now adopts an existing task dir whose slug matches modulo a ticket prefix, in either direction, and
tells the command which key to use; unrelated tasks still get their own dir.

- **0.48.1** — **Two agents in one repo no longer report each other's task.** `state.md` was picked
by mtime, so every session rooted in a repo showed whichever task had been touched last: start a
second agent there and both rows flipped to the same task, stage and tier. The hook now records
which task dir each session actually writes (or the task named in its `/anderson:` command) and
fleet reads that session's own state.md. Sticky across events that say nothing about the task, and
sessions with no hooks keep the old mtime fallback.

- **0.48.0** — **The tier is visible everywhere the work is.** The difficulty tier already decided
what the review gates cost, but you had to dig for it. It now leads the plan (a `**Tier:**` line
directly under the H1, above 🎯 What, instead of buried in the Scorecard), rides the PLAN_REVIEW
banner so you see it before the critique starts, and has its own column on the fleet overview —
`triv · normal · HARD · CRITICAL`, upper-case for the two that buy a heavier review — so a screen of
rows shows at a glance which agents are grinding and which are coasting.

- **0.47.0** — **A busy repo gets a worktree, not a hijack.** Spawning an agent onto a repo that is
already parked on a feature branch used to drop it straight into that checkout, on top of whatever
was in flight there. Now the agent gets its own worktree — `.worktrees/<task>` on `anderson/<task>`,
cut from the default branch (`origin/<default>` when it exists) — and the repo keeps its branch and
its uncommitted work. On the default branch nothing changes: the checkout is free, the agent uses it.
Anything git refuses falls back to the repo with a note, so a spawn is never blocked. Sessions
running in a worktree still row under the repo they came from, not in `elsewhere`.

- **0.46.0** — **The monitor stays put, and you can hide a repo.** Spawning an agent used to take
over the window fleet was in: it now opens a terminal of its own (a real OS window on macOS, a `-d`
tmux window elsewhere), so the fleet you launched from is still there when the agent starts. The
prompt box was a dim quote line nobody could find while typing, and is now a solid bar with a block
cursor. `b` on a repo or group row hides that repo and its agents, saved per workspace like order and
collapse; `h` lists the hidden ones, folded and dim, and `b` brings one back.

- **0.45.0** — **`fleet update` updates the plugin.** The shim in `~/.local/bin` already resolves the
newest cached version at run time, but nothing told you a newer one existed, so a machine could sit on
an old fleet for weeks. `fleet update` now refreshes the marketplace, updates the plugin through the
`claude` CLI, and prints the version it moved from and to (or that you were already current); restart
Claude Code to apply. No `claude` on PATH, it points you at `/plugin update anderson` instead.

- **0.44.0** — **Fleet becomes the place work starts.** Rows are now the repos of the workspace fleet
was launched from, one nested level, with live sessions underneath their repo and collapsible groups.
`J`/`K` order and the collapsed set persist per workspace, and `⏎` on a repo or group row spawns a
claude agent into it as a tmux window, so the monitor no longer needs an IDE to begin work in.
Behaviour change: `fleet` outside tmux attaches a per-workspace tmux session by default, and
`⏎ · J/K · space · D` have new meanings.

- **0.43.0** — **It counts its own installs.** A marketplace install is a shallow clone, which GitHub's
traffic API counts; an update is a fetch, which it does not. So the plugin says hello once per version
per machine: a SessionStart hook fetches the one-byte `ping` asset attached to that release, and
GitHub's public `download_count` on the asset is the number. Nothing is sent but the request itself —
no identifier, no path, no machine or user information, no third-party service. Opt out with
`ANDERSON_NO_TELEMETRY=1` or the cross-tool `DO_NOT_TRACK=1`, and the hook never runs. See
[Install counting](#install-counting).

- **0.42.0** — **The plan states its own price.** The tier decided what the review gates cost and
which models ran them, but only `state.md` knew it. `plan.md` now carries a `**Tier:** <TIER> —
plan_review <model>/<effort> · implement sonnet/medium · diff_review <model>/<effort>` line under
`## 📈 Scorecard` (the planner seeds it `pending`; routing fills it in, the plan-reviewer leaves it
alone), the Gate 1 card echoes the same line, and the re-tier at the diff gate rewrites both with
`was <old>` when it escalated — so a silent price change is no longer possible and you see the bill
before you approve it. Also fixes a stale README footnote that still claimed diff-review effort was
a fixed `high`/`xhigh` off Risk ≥ 8, which tiering replaced in 0.40.0.
- **0.41.0** — **Fleet: ⏎ revives a sentinel.** A dead row had nothing to jack into, so 0.40.2 told
you to press `c` and paste the command yourself. Now `⏎` gives that session a terminal: a new tmux
window when fleet runs under tmux, else a new iTerm2 / Terminal.app window (AppleScript), already
running `cd <cwd> && claude --resume <sid>`. `c` still copies, and off macOS/tmux — or when
AppleScript is refused — revive falls back to that copy with the reason.
- **0.40.4** — **Fleet: the AXRaise fallback goes.** 0.40.2 retried a failed raise through System
Events AXRaise. Measured against a real cross-Space window it never helped: AXRaise cannot pull a
window off another Space, and aiming it needs a window title, which in Terminal carries the running
command and changes between the lookup and the raise (`Can't get window 1 of process`). One 2 s wait
replaces the two-stage retry, and when the window really did stay put the message carries the whole
one-time fix, `killall Dock` included: without that restart the `workspaces-auto-swoosh` default is
written but not live, which is exactly how a jack in needed two presses.
- **0.40.3** — **Fleet: ⏎ across Spaces lands on the first press.** Raising a window that lives on
another Space costs a full-screen Spaces animation first, about a second, and the 0.6 s check added
in 0.40.2 gave up before it finished: the first ⏎ reported that the window had stayed behind, and a
second ⏎ then worked because the Space had already changed. The check now waits up to 1.4 s, retries
through AXRaise, and waits 1.6 s more, exiting the instant the tab is in front — a same-Space jack in
still returns in about 0.3 s.
- **0.40.2** — **Fleet: ⏎ actually moves you there.** Three fixes to the jack in. The focus script
now `activate`s the terminal *before* reordering its windows: with one tab per window (six Terminal
windows, say) activating afterwards handed the raise back to the app's own front window. The result
is then verified — the frontmost tab's tty, not the AppleScript's "ok", which is reported for
selecting a tab whose window never came over — and on a miss it retries once through AXRaise before
saying the window stayed on another Space, with the one-line `defaults write
com.apple.dock workspaces-auto-swoosh` fix. And ⏎ on a dead row now says the process is gone and
points at `c` / `b`, instead of talking about tmux.
- **0.40.1** — **Fleet: ⏎ means move me there.** Jacking into a session parked at a human gate no longer
reports "no IDE owns that session" when a plain terminal owns it: the auto-open is silent unless a GUI
editor actually applies, so a successful jack in stops reading like a failure. `O` still says why nothing
opened, since asking for the IDE is the point of that key. Landing images in both READMEs are now real
stills of the fleet boot screen and the live board (`assets/*.tape` on the `media` branch re-records them with VHS), replacing
the hand-maintained ASCII mock.
- **0.40.0** — **Tiered review effort in start mode.** The gated loop derives plan-review and diff-review
effort from the plan Scorecard instead of running both at a fixed xhigh: a trivial tier skips plan-review,
critical runs both gates at xhigh.
- **0.39.0** — **Fleet: see what the subagents are doing.** On a tall terminal the card lists the running subagents
live under `agents` (`↳ anderson:reviewer "Diff-review AR-2598" · ▶ Grep process_order · 40s`), read from their
own transcripts in `<session>/subagents/`. `a` pages the newest one (running first) as a readable log: its words,
the tools it called, a line of each result. `q` returns.
- **0.38.4** — **Fleet: one row per session, really.** Claude Code's background daemon (`claude daemon` →
`bg-spare`, `bg-pty-host`) runs under your session with its own session ids and fires the same hooks, so a
session could show up three times. Any session whose process descends from another claude process is now
folded away, whether fleet found it by ps or by its hook / heartbeat files.
- **0.38.3** — Fleet: `o` with glow now uses the full terminal width (glow wraps at 80 columns unless told).
- **0.38.2** — **Fleet: idle goes white.** A ring older than 5 minutes stops pulsing and paints white, steady;
it still sorts with the rings and still needs you, it just stopped shouting. Fresh rings pulse as before.
Also repairs the changelog: a careless version bump had rewritten the number on every entry since 0.34.4.
- **0.38.1** — **Fleet: extras installer + requirements list.** `fleet install` reports the optional tools
(glow, terminal-notifier, tmux) with ✓ / missing and the exact install line; `fleet install --extras` installs
glow and terminal-notifier, `--all` adds tmux. `/anderson:fleet` now forwards its flags (`--extras`,
`--with-tmux`, `--all`). New "What fleet needs" table in both READMEs.
- **0.38.0** — **Fleet: read the plan where you are.** `o` now opens plan.md / audit.md inside the fleet terminal
(glow when installed, else `less -R` over a small stdlib markdown colouring: headings, bullets, **bold**, the
reviewer's ~~strike-through~~, code); `q` comes straight back. `O` keeps the IDE route (--editor, GUI $VISUAL,
or the IDE owning the session). Sessions owned by a plain terminal no longer fall back to `open` into whatever
app claims .md files; they say so and point at `o`.
- **0.37.5** — Fleet: full repaint every 10 s and on ctrl-L. The diff repaint only redraws lines it knows changed,
so a Space swipe or an app switch that made the terminal drop cells left stale garbage until the next resize.
- **0.37.4** — Fleet: one more blank line between the list's rule and the card on tall terminals.
- **0.37.3** — **Fleet: room to breathe, part two.** On a tall terminal (16+ free lines) blank lines sit around the
header rule and between the list and its rule; short terminals stay dense.
- **0.37.2** — **Fleet: usage moves to the top.** The plan's windows now sit right under the title, with a bar each
(`matrix · session ▓▓▓▓░░░░░░ 42% · 3h39 left │ week ▓▓▓▓▓░░░░░ 52% · resets Fri 19:00`), red past 90%. The footer
keeps the keys only; API-key users (no windows) still see the api estimate down there.
- **0.37.1** — **Fleet: no ping when you're already there.** A ring skips the desktop banner and the sound when the
session's own terminal is frontmost (the Terminal.app / iTerm2 tab showing its tty, the active pane of an attached
tmux session, or the IDE that hosts it); the toast in fleet still says who needs you. `fleet --ping` sends a test
banner through every channel and says where to look in System Settings when none shows.
- **0.37.0** — **State first.** `/anderson:start` now seeds `feature-research/<task>/state.md` in a shell preamble,
before the model reads a single line, so the fleet row (task, ARCHITECT, plan 0/2) appears within two seconds
instead of after the planner warms up. New `feature.sh seed [--opus] <task>` does exactly that and nothing else
(idempotent: an existing state.md is left alone).
- **0.36.2** — **Fleet: `h` shows the hidden rows** (flagged `◌`, dim, counted in the header); `b` on one brings it
back. A few footer keys wear a marker so the eye finds them: 🔴 kill · 🔵 hide · 👻 hidden · 🔔 notify ·
🔊 sound · 🎵 ring · 🔍 filter · 🎨 theme (unicode terminals only; `--ascii` stays plain).
- **0.36.1** — **Fleet: kill hides, hide never kills.** `r` (kill, asks first) now hides the row as soon as the signal
is out; `b` hides any row, live or dead, without touching the process (a hidden live session stays hidden).
Footer says `r kill · b hide`; the pills live on in the manual and the toasts.
- **0.36.0** — **Fleet: the footer moves to the floor.** Keys and usage now sit on the last lines of the terminal, each on
its own line (keys wrap between groups, never truncate; usage reads alone). The detail card keeps the whole middle.
New `agents` line in the card: how many subagents the session sent, how many are running, and the last one
(`4 sent · 1 running · last anderson:reviewer "Diff-review AR-2598" (fable)`), read from the transcript's
`subagents/` folder.
- **0.35.1** — `fleet --play all` auditions every ring sound from the shell (`--play NAME` for one); `--rings` says so.
- **0.35.0** — **Fleet: pick your ring.** Seven bundled sounds in `assets/sounds/` (phone, the Matrix call, stays the default;
plus snare, hitech, freeze, blip, rift, jump, each cut to its loudest ≤2.5 s and normalized). `s` cycles with a
preview and saves the pick, `--ring NAME` / `--rings` from the shell, and any `.wav` you drop in
`~/.claude/fleet/sounds/` joins the list by name. `~/.claude/fleet/ring.wav` still overrides everything.
Licenses in `assets/NOTICE.md`.
- **0.34.4** — **Fleet: one process, one row.** Headless `claude -p` children spawned inside a session (reviewers, hooks) no longer show up as a second session of the same repo, and after `/clear` or `/resume` only the process's current session id is listed.
- **0.34.3** — **Fleet: room to breathe.** With 16 or more free lines the detail card goes airy:
  blank lines between the three groups (task · who · verdicts │ status · context · where │ prompt ·
  last · next), an 11-cell label column, and `last` wraps to two lines instead of truncating. Ten to
  fifteen free lines keep the compact card; fewer keep the three-line form.
- **0.34.2** — **Fleet: one full ring.** The bundled phone is now exactly one ring (2.43 s, 0.97 s →
  3.40 s of "Full Matrix", boundaries found by energy scan) instead of a 1.25 s cut that stopped
  mid-ring. Same CC0 source, cut from the Pixabay copy of the file.
- **0.34.1** — **Fleet: the Matrix phone.** The ring is now a 1.25 s cut of the telephone ring from
  "Full Matrix" by skycarl (Freesound #210499, **CC0**), bundled as `assets/ring-matrix.wav` with
  attribution in `assets/NOTICE.md`. Precedence: your `~/.claude/fleet/ring.wav`, else the bundled
  phone, else the synthesized ringback.
- **0.34.0** — **Fleet: the phone rings; honest usage numbers.** `m` (or `--sound`) plays a
  synthesized ringback tone (440 + 480 Hz, two bursts, stdlib-generated into
  `~/.claude/fleet/ring.wav`, replace the file for your own sound) when a session starts waiting on
  you; `afplay` on macOS, `paplay` / `aplay` on Linux. The footer's `/usage` windows are the last API
  reply any session saw, since fleet cannot query the API itself: numbers older than two minutes now
  carry `(as of 4m ago)`, and copies older than six hours are dropped rather than shown wrong.
- **0.33.1** — **Fleet: detail card; red footer at 90% usage; test fix.** When the terminal has
  ten or more free lines below the table, the selected session gets a labelled card instead of three
  dense lines: `task` (with repo and `⎇ branch`), `who` (persona · stage · model · tier), `verdicts` (plan,
  diff, gate), `status` (what it does now, last activity, session age), `context` (bar, tokens,
  lines ±, `← /compact` past 80%), `where` (pane, pid, session id), `prompt` (first prompt when an
  anderson task is running), `last` (last words), **`next`** (the one thing you do now: which command,
  which file). Small terminals keep the compact form. The footer paints red when any `/usage` window
  passes 90%, since extra-usage credits come right after. 0.33.0 shipped with one failing test (an
  exact-dict prefs assertion that predates the `editor` pref); fixed, and the release pipeline now
  merges only on green CI.
- **0.33.0** — **Fleet: open the gate artifact in your IDE.** `o` opens what the current stage wants
  read: `plan.md` for grill and plan review, `plan.md` + `audit.md` for diff review, `audit.md`
  during implement. Jacking into a row parked at a human gate (`gate: human`) does it automatically,
  so `⏎` lands you in the session *and* on the plan. Editor resolution: `fleet --editor code`
  (saved), else a GUI `$VISUAL` / `$EDITOR` (code, cursor, zed, subl, webstorm, idea, pycharm…), else
  the IDE that owns the session (WebStorm / VS Code integrated terminals), else the OS default opener.
- **0.32.2** — **Fleet: reliable macOS notifications.** `osascript` banners are often swallowed on
  recent macOS and never register an app in System Settings. `notify()` now prefers
  `terminal-notifier` when installed (`brew install terminal-notifier`): banners show, the app is
  listed under Notifications, and clicking one brings the terminal fleet runs in to the front.
  Pressing `n` sends a test banner and, when the tool is missing, says how to install it;
  `fleet install` prints the same hint on macOS.
- **0.32.1** — **Fleet: context alert.** When a live session crosses 80% context the monitor toasts
  `context 84% on <repo> · <task>: /compact before it eats the budget`, and pings the desktop when
  `n` notifications are on. Once per crossing; a `/compact` that drops it below the line re-arms it.
- **0.32.0** — **Fleet: navigation and overview batch.** Sessions with no anderson pipeline show
  their first prompt as a quoted title instead of `(no anderson task)` (a `/resume` summary wins when
  Claude Code wrote one; titles survive on sentinels so you know what to resume). Ringing rows say
  for how long: `☎ ring 12m`, `☎ permission Bash 3m`, `☎ idle 4h`. The ctx cell paints red past 80%
  (`/compact` before the next review panel). Rows are numbered; `1`..`9` jack straight into row N.
  `c` copies `cd <cwd> && claude --resume <sid>` to the clipboard (pbcopy / wl-copy / xclip, else
  shown), so a sentinel is recoverable, not just dismissable. `⎇ branch` in the detail line now
  comes from the transcript's `gitBranch` for every session, not only anderson ones. `n` (or
  `--notify`) turns on a desktop notification when a session starts ringing (macOS Notification
  Center, Linux `notify-send`), saved in prefs.
- **0.31.2** — **Fleet: closed sessions die on screen.** A session whose emitter never recorded a
  usable pid (files written before 0.31.1, or a session older than the hooks) had no liveness
  signal, so closing it left the row up until the 24h expiry. Now: pid unknown + no `claude` process
  in that cwd = `✝ sentinel`. `b` still dismisses it.
- **0.31.1** — **Fleet: real pids, no duplicate rows, idle detection, column caps.** The heartbeat
  and hook emitters reported pid 1: the backgrounded emitter is reparented to launchd, so `getppid()`
  lied. Effects: sessions never became sentinels, `ps` discovery added a duplicate row for the same
  session matched to a stale transcript, jack-in by pid failed. Emitters now walk the ppid chain to
  the real `claude` process (`FLEET_PID` handed down by the statusline shells); fleet treats pid ≤ 1
  as unknown and adopts the `ps` process in that cwd instead of duplicating. A "thinking" session
  with no transcript activity for 15 minutes is shown as `☎ idle` (interrupted turn, waiting on you).
  Repo/task columns cap at 28/56 cells so ultra-wide terminals stay readable.
- **0.31.0** — **Fleet: usage in words, `$` opt-in, `fleet` runs in place.** Footer now reads
  `session 46% · 4h07 left │ week 41% · resets Fri 19:00` (the `/usage` windows: the rolling 5-hour
  "current session" and the 7-day all-models window; Claude Code exposes no per-model weekly number
  and no plan price, so on a flat-fee plan these percentages are the cost). The `api$` column and
  footer estimate are hidden on subscriptions; `$` or `--cost` shows them as a burn gauge; API-key
  users (no limits) still see them by default. `fleet` now runs in the current terminal whether or
  not tmux is around; `fleet --tmux` opts into the persistent tmux session, with its status bar off.
- **0.30.1** — **Fleet: zoom.** Font size belongs to the terminal, and Terminal.app exposes it per
  window over AppleScript, so `fleet --zoom 16` (or `+` / `-` while running) grows the window's font
  for the monitor and restores the original size on quit. Saved in `prefs.json`; `--no-zoom` clears.
  iTerm2 and IDE terminals have no font API: the toast says ⌘+ / ⌘-.
- **0.30.0** — **Slugs with a slash stay flat; ship on that branch.** Pasting a branch name as the
  slug (Linear style, `user/ar-2587-ui-polish`) used to nest the state dir
  (`feature-research/user/ar-2587-…/`), invisible to the statusline, the scheduler, `/anderson:status`
  and the fleet monitor. The task key is now the LAST `/`-segment, so the dir is always
  `feature-research/<key>/`. When the slug had a `/` it is recorded as `branch:` in state.md and
  `approve-diff` / `feature.sh --approve-diff` ship on it verbatim instead of `anderson/<key>`, so
  the branch matches the ticket. Every command resolves the key the same way; fleet's detail line
  shows `⎇ <branch>`. `test/test_feature_slug.py` proves flat dir, `branch:` seed, and ship branch.
- **0.29.3** — **Fleet: subscription usage in the footer; honest `$`.** The heartbeat now records
  Claude Code's `rate_limits` (the `/usage` numbers: 5-hour and 7-day windows, used % and reset time)
  and the footer shows them: `zion $115.28 · 5h 20% ↻4h33 · 7d 37% ↻Fri`. Account-wide, so the
  freshest heartbeat is the truth. The `today $` total is gone: it summed lifetime per-session costs
  and read as a daily bill. `$` is documented for what it is, Claude Code's client-side estimate at
  API list price, notional on a subscription, a gauge of which session burns most.
- **0.29.2** — **Fleet: jack in reaches IDE terminals.** When a session runs in an integrated
  terminal (WebStorm, VS Code, Cursor, Warp...) no tab is scriptable, so `⏎` now walks the process
  ancestry to the owning `.app` and brings it forward, with a toast saying the tab itself could not
  be selected. Order stays: tmux pane → iTerm2/Terminal.app tab by tty → owning app.
- **0.29.1** — **Fleet: jack in without tmux; tmux optional.** `⏎` now falls back to the session's
  tty: on macOS it focuses the iTerm2 / Terminal.app tab that owns the Claude process (AppleScript),
  so sessions started in plain terminal tabs are one keypress away too. When the monitor runs outside
  tmux and the session is in a pane, the pane is selected and the tab holding that tmux client is
  focused. `fleet install` no longer assumes tmux: it says tmux is optional and offers
  `fleet install --with-tmux` (brew / apt / dnf). Manual, card and READMEs follow.
- **0.29.0** — **THE OPERATOR: `bin/fleet.py`, the cross-repo fleet monitor.** One terminal for
  every Claude Code session on the machine: repo, anderson task, persona on the job, stage, model,
  what it does right now, $, context, age; ⏎ jacks into the session's tmux pane. Runs outside Claude
  (stdlib curses, zero tokens). Zero-setup discovery via `ps` + transcript tail + `state.md`; this
  plugin's hooks add the exact waiting/working signal (`hooks/fleet_event.py`); the statusline
  heartbeat (`bin/heartbeat.py`, called by `statusline.sh` or the new `fleet-statusline.sh` wrapper
  around any statusline) adds cost and precise context. Five themes (`matrix`, `construct`, `zion`,
  `nebuchadnezzar`, `agent`), Matrix-or-plain wording and motion are per-user prefs in
  `~/.claude/fleet/prefs.json`. Repaints only changed lines (no flicker). Alignment is a tested
  invariant (`--selftest`, `test/test_fleet.py`). Boot screen with a line that rotates every launch.
  `/anderson:fleet` installs the `fleet` launcher (tmux-aware, stable across plugin updates) and prints the card. Loop unchanged.
- **0.28.0** — **Fable is the default critic; `--fable` becomes `--opus`.** The `reviewer` and
  `plan-reviewer` agents now declare `model: fable` in frontmatter, and `review_model` seeds to
  `fable`; the inverse flag `--opus` (on `start`, `auto`, `feature.sh start`) runs both critique
  gates on Opus instead. Rationale: Fable is the stronger critical analyst, and Fable 5.1 cache
  reads are priced far below prior tiers, so the plan + diff context re-read by the panel and
  arbiter is cheap to serve. Generative stages (planner opus, implementer sonnet) unchanged.
  Missing `review_model` in an older `state.md` now resolves to `fable`. Banners, matrix demo,
  statusline fallback, and both READMEs follow. **Reviewer effort tiered:** `reviewer` frontmatter
  drops to `high`; `xhigh` only for hard/critical panelists, the arbiter, and gated diff reviews where
  the Scorecard has Risk ≥ 8 or the change touches security / memory / OS boundaries. Plan-reviewer
  stays `xhigh`. **Two Fable 5.1 prompt snippets** (from Anthropic's prompting guide): both reviewers
  batch independent reads into one turn; the plan-reviewer edits `plan.md` surgically instead of
  rewriting it.
  **Prompt audit** (`/claude-api prompt-audit`): quote-selection arithmetic replaced by "pick one",
  duplicated quote pools collapsed, `auto.md` override-policy changelog rewritten as current rules,
  sequencing/banner rules restated once at normal volume, dead self-review reference and attribution
  asides removed. −130 lines of command surface. Bench (2×2, same fixture, `/anderson:approve-plan`):
  sequencing held in 4/4 runs; reviewer verdict vocabulary now valid in 2/2 (was `rework` 2/2 before);
  cost −36%, wall time −40% (confounded with the reviewer effort drop).
- **0.27.0** — **Dated model IDs removed, per-token prices dropped, persistent override
  documented, statusline follows the active review model.** The two dated model-ID strings in
  `docs/auto-mode-handoff.md` are gone, along with the per-token figures next to them — a new CI
  step now fails the build if any tracked file quotes a paired per-token price. `settings.json`
  `env` (`CLAUDE_CODE_SUBAGENT_MODEL` / `ANTHROPIC_MODEL`) is documented as the supported way to
  pin every stage to one model permanently, not a gotcha to clear. The statusline now reads the
  active review model (`fable`/`opus`) instead of always showing Opus under `--fable`. Version
  sites re-synced across `plugin.json`, `marketplace.json`, and both README badges.
- **0.26.0** — **Outcome-shaped criteria, load-bearing assumptions, one proof per criterion, and
  multi-repo contract verification.** Acceptance criteria are now observable outcomes (`When X → Y`,
  actor's POV — never a restated How), capped to what's provable AND load-bearing. `## ✅ Decisions`
  classifies each assumption **LB** (feature is wrong if the guess is wrong) or **safe**; the plan
  gate **blocks** while any LB row is unconfirmed (gated: the grill can't defer it; auto: the
  plan-reviewer ratifies with a basis or ships it as `needs-human`) — a guessed target can no longer
  pass every downstream check. Every criterion now needs its OWN discriminating proof that fails if
  that criterion breaks (no shared/blanket evidence, no `#n covered by #m`) — the silent
  edge/failure-case bug now needs executable proof, not a reviewer's eyeball. Multi-repo tasks gain a
  mandatory `source: contract` seam criterion proven against a frozen fixture both repos pin, a
  `⚠️ Merge order` line on the primary PR, and `Blocked by` links on companions. `visual` proof is
  state-driven (a screenshot per outcome-state, not one happy-path shot).
- **0.25.0** — **⚠️ Behavior change section + design moves up.** The planner adds a `## ⚠️ Behavior
  change` line (≤2 lines: the "so what" — what observably changes for a user/caller/API, or
  "none — internal only") right after Why. New plan read order: What → Why → ⚠️ Behavior change →
  🗺 Design → ✅ Acceptance criteria → 🛠 How → 📈 Scorecard (Design promoted above the criteria).
  Both ship paths carry the behavior-change line verbatim into the PR body (omitted when
  internal-only) and match the same order (Design before criteria). **Proof is now displayed,
  not just named:** the implementer tees each e2e run to `evidence/*.e2e.log`; both ship paths
  embed that log in a per-criterion `<details>` collapse under the criteria table (the ephemeral
  script's only record — it never reaches CI), and post visual screenshots as a PR comment
  (gist-hosted, since `gh` can't inline-upload), degrading to the gate-verified text note on any
  failure. Test proofs stay named-only — the diff + CI already show them.

- **0.24.0** — **PR body is the plan minus the how.** Both ship paths (`/anderson:approve-diff`
  + `/anderson:auto` step 8d) now build the PR from the plan's durable sections instead of dumping
  the whole plan into one collapse. Visible, in read order: What & why, the acceptance-criteria
  table with evidence, the design (lifted out of its plan collapse), and a reviewer-facing
  **How to test** section — the test command, manual steps, and a `**Config required:**` line for
  new env vars / flags / deps. Scorecard, blast radius, and error handling drop into `<details>`
  collapses below. The **🛠 How and ✅ Decisions are excluded** — the diff is the how, no double-up.
  Open-questions still print only when there are deferred business calls. The old verbatim "Full
  plan" collapse is gone: the structured sections are now the plan's durable GitHub home.
- **0.23.0** — **Acceptance criteria with proof, design intake, and a leaner read.** Three
  moves, one theme: verify against explicit criteria instead of vibes, and show humans only
  what they need.
  - **✅ Acceptance criteria table** (`# | Criterion | Source | Proof | Evidence`) is now the
    plan's spine, in BOTH modes. Sources: `ticket` (verbatim), `design` (exact strings from the
    design inventory), `derived` (planner judgement — the gated grill confirms each as a 🔴
    question; auto's plan gate checks coverage as before). The plan-reviewer blocks on a
    missing table, an unmapped criterion, or paraphrased design copy.
  - **Design intake** — `/anderson:start` (step 2b) and `/anderson:auto` (step 1g) normalize
    any referenced design — Figma URL, ticket screenshot, or image file — into
    `feature-research/<task>/design/` (PNGs + `inventory.md`: every exact string, state, and
    layout fact). Fixes the "built it, doesn't match the design" gap at its root: the criteria
    and the reviewer now have the reference artifact.
  - **Evidence or it didn't happen** — the implementer must fill the Evidence column (its only
    permitted plan.md edit): `test` (must fail without the change), `visual` (screenshot of the
    running UI into `evidence/`, compared against `design/` by the reviewer), `e2e` (ephemeral
    script in scratch — gate-time only, deleted at ship, never wired into CI; `promote
    candidate` flags a flow worth keeping), or `manual` (only when nothing executable covers
    it). The diff reviewer gained a blocking **criteria-evidence lens**: runs the tests, opens
    the visual pairs, blocks on blank cells, worthless tests, or any text/layout mismatch —
    reported as `criteria: proven/total`. Auto's correctness panel lens carries the same check.
  - **Leaner plan.md** — human-first read order (What → Why → Criteria → How → Scorecard
    visible; Design / Blast radius / Error handling / Decisions bodies in `<details>`
    collapses) with hard word budgets the plan-reviewer enforces. Fewer tokens for every
    downstream agent, not just fewer lines on screen.
  - **Gate TL;DR cards** — both gates now halt on a card (what · criteria/proof counts ·
    scorecard · verdict; Gate 2 lists failed criteria with the reviewer's one-line why), so
    reading the full plan becomes the exception.
  - **Leaner PR body, both ship paths** — visible: Source (when present) · What & why ·
    criteria table with evidence · scorecard; Setup and Open-questions print ONLY when
    non-empty; How-to-test is absorbed by the evidence column + one `test:` line; review
    detail, audit, metrics, and the full plan stay in collapses. Gated `state.md` gains
    `source_url:` (additive) so the ticket link survives to the PR.
- **0.22.0** — **`/anderson:help` quick-reference card.** New one-shot command that prints a static
  card with every command, its arguments, the two gates, and the `--fable` flag. Reads no state,
  spawns no agents — the live dashboard stays `/anderson:status`. Both READMEs' command tables
  gained the row.
- **0.21.0** — **Plan-reviewer judges the frame first.** Before line-editing, the plan-reviewer
  now asks "would I have planned it this way?" — a wrong approach gets rewritten in place (with
  read scope widened to what the rewrite needs) or routed `regrill`, instead of being patched
  line by line. Closes the anchoring gap in the `--fable` review gate.
- **0.20.2** — **Grill instruction cleanup.** Removed the now-redundant "assume I know the code"
  instruction bullet: the 3-line question card already enforces terse, context-free questions and
  the 🟢 batch handles preferences, so it was saying twice what the format already guarantees.
  Behavior is unchanged; the grill still never asks about code familiarity.
- **0.20.1** — **Grill drops the familiarity question.** The grill no longer opens with the
  "How familiar are you with <touched area>? wrote it / know it / new to it" calibration line. It
  now assumes you know the touched code: terse questions, no per-question context sentences,
  borderline 🟢 auto-resolved to the recommendation. One less meta-question before the real ones.
- **0.20.0** — **Slimmer, calmer grill.** The interrogation step was too busy — a 3-line manifest
  with a per-vector "blindspot sweep" line, two-line question headers, and eight competing emoji.
  Now: a **one-line manifest** (`grill · N questions · a🔴 b🟡 c🟢` + a rule), and each question is
  a **3-line card** — `🔴 n/N ▰▰▱▱▱▱▱▱▱▱` (the grade dot is the only emoji; the bar is 10 cells,
  filled = round((n−1)/N × 10) so it grows as answers land), the question, then `→ recommendation`.
  When an answer spawns a new question the total grows in place with a dim `+1 from your last
  answer` note — no manifest reprint. **The standalone blindspot sweep is gone**: the planner
  already maps blast radius at plan time, so the grill now challenges that table's completeness
  directly (grepping a specific caller only when it doubts a row) instead of re-sweeping five
  vectors on every run. Less ceremony, same catch, a screen you can think in.
- **0.19.0** — **`--fable` opt-in for the review gates.** New state field `review_model` (default `opus`)
  runs the two critique stages — PLAN GATE plan-reviewer, DIFF GATE reviewer panel + arbiter — on Fable
  instead of Opus when a pipeline is started with `--fable`. Fable is the stronger critical analyst; the
  generative stages (planner, implementer) stay on Opus/Sonnet and the flag never touches them. Effort
  stays xhigh. The choice is seeded once at pipeline init and persists in `state.md`, so it carries across
  the resumed `approve-plan`/`rework` sub-commands; `feature.sh start … --fable` and `/anderson:auto …
  --fable` both honor it. In auto mode the panel's HARD/CRITICAL tier + arbiter follow `review_model`
  (`panel_model` metric gains a `fable` value); TRIVIAL/NORMAL panelists stay on the cheap tier.
- **0.18.0** — **Ponytail ladder + caveman-compressed instructions.** Two token cuts, different axes:
  - **Ponytail decision ladder** (after [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail),
    MIT) inlined into all four agents — anderson stays self-contained, no plugin dependency. Before any
    new function/module/abstraction/dependency: does it need to exist? → already in the codebase? →
    stdlib/platform? → existing dep? → one line? → only then minimal new code. Planner plans least-code,
    implementer writes least-code (no speculative params, no single-call-site helpers), plan-reviewer
    edits excess down in place, diff-reviewer runs a YAGNI lens (blocking when excess adds a dependency
    or public surface). Safety rungs exempt everywhere: validation, security, accessibility, error
    handling are never cut. Less code generated = fewer output tokens now, fewer input tokens every
    later read of that code.
  - **Caveman-compressed command prose** — instruction files are input tokens paid on EVERY run;
    compressed instructional prose only (articles/filler dropped, duplicate sentences merged), all
    byte-faithful blocks untouched: quote pools (3×24 verified), state.md template + STATE markers,
    banners, git/gh command lines, verdict values. start.md −12% chars (the quote-picking algorithm,
    repeated verbatim per banner, is now one QUOTE RULE + per-banner offset); approve-plan −6%,
    rework −5%, approve-diff −4%, auto.md −2% (deliberately conservative — it runs unattended).
    Single revertible commit in case compliance regresses. **Graded grill with upfront triage.** The grill previously streamed questions
  open-endedly: no sense of how many were coming, which ones mattered, and only questions the plan
  already knew it had (its own decision tree) ever got asked. Now:
  - **Triage first** — THE INTERROGATOR enumerates every question in one pass (decision-tree
    branches + 🧯 `needs-context` rows + 💥 blast-radius gaps) **plus a structured blindspot
    pass** over what plan.md never mentions, sweeping five concrete vectors (callers, tests,
    config/flags, git history, repo conventions) rather than one free-form look — the manifest's
    sweep line (`callers ✓ · tests +2 · …`) proves each vector was checked. Anything the
    codebase can answer is answered there, never asked.
  - **Calibration (question 0)** — one line, "wrote it / know it / new to it", tunes question
    depth to your familiarity with the touched area; never more than this one meta-question.
  - **Token economy** — the sweep is scoped to the plan's touched files/symbols (grep/git-log
    one-liners, excerpts, no repo-wide scans), preferably delegated to one cheap read-only
    search subagent so the greps never enter the main session's context; trivial plans collapse
    it to a single grep + git-log pass. Turn count cut too: independent 🟡 pair 2–3 per message,
    each question capped at 4 lines (header + question + recommendation, no plan restating).
  - **Grades** — every question is classed 🔴 ARCH (answer changes architecture/data model/scope),
    🟡 BEHAVIOR (edge cases, error handling, UX semantics), or 🟢 PREF (safe to default).
  - **🔥 Manifest** — printed before question 1, so you see the grilling level upfront: total count,
    per-grade split, and the per-vector blindspot sweep line.
  - **Progress header** — each question carries `❓ n/N · grade` + a bar; follow-up questions grow
    N honestly instead of hiding the drift. Order is strictly 🔴→🟡→🟢 (early answers constrain
    later ones); all 🟢 are batched into one message a single "defaults fine" accepts.
  - **Early exit is now safe** — "good, go to review" auto-resolves remaining 🟢 to recommendations
    (`[answered] … (grilled, default)`) and records remaining 🔴/🟡 as `[open]`; skipping never
    silently decides the big ones.
  - `/anderson:demo` annotated to match. (Same triage/grade/manifest model also backported to the
    standalone `grill-me` / `grill-with-docs` user skills, minus state.md bookkeeping.)
- **0.16.0** — **Open-questions parity for the gated path.** 0.15.0 wired the 🧯 error-handling →
  open-questions flow into `auto` but only half into the gated loop: THE INTERROGATOR *walked* the
  `needs-context` rows in the grill, but a deferred row had nowhere to be recorded and never surfaced
  in the ship PR (it survived only buried in the full-plan collapse). Now symmetric with auto:
  - **`/anderson:start`** — the seeded `state.md` gains an `open_questions:` field + a
    `## ❓ Open questions` section. The grill records each row it resolves or defers there, using
    auto's convention (`[answered] … → … (grilled)` / `[open] … — <why>`), and sets the count.
  - **`/anderson:approve-diff`** — the PR body now leads with a visible `## ❓ Open questions &
    assumptions` block (🔴 deferred / 🟢 resolved) lifted from `state.md`, so a reviewer sees the
    open business calls without unfolding the plan; the PR is labelled `needs-human` when any
    `[open]` row remains (graceful — drops the flag if the label or `gh` is unavailable).
  - **`/anderson:demo`** — annotated so the dry-run preview reflects the grill's 💥/📈/🧯 walk and
    the open-questions section the ship PR now carries.
  - Headless `bin/feature.sh` is unchanged (it has no grill stage, so it can't produce open
    questions the same way).
- **0.15.0** — **Error handling as a planning concern + auto-mode open-questions report.**
  - **🧯 Error handling section (planner)** — every plan now enumerates the failure paths the change
    touches (derived from the blast radius, not guessed) and classes each `deduced` (handle it now)
    or `needs-context` (a business call the code can't make). Anchored in THE ARCHITECT, folded in
    silently — no new persona, no new stage.
  - **Verified at both gates** — THE ORACLE (plan-reviewer) treats a missing failure path or a
    `needs-context` row not mirrored in ✅ Decisions as **blocking**; the diff-review correctness lens
    (AGENT SMITH, gated + auto panel) checks every `deduced` row is actually handled.
  - **Gated** — THE INTERROGATOR walks the `needs-context` rows in the grill: you decide the handling,
    the row re-classes to `deduced`.
  - **Auto** — no grill, so step 4g captures the ambiguities into state.md `## ❓ Open questions`
    (`[open]` = needs a human, `[answered]` = auto's assumption). They surface in a new PR section
    **## ❓ Open questions & assumptions**, force the `needs-human` label when any `[open]` remains,
    and add `open_q=<n>` to the `metrics:` line + REPORT block. Auto ships the question, never an
    invented business answer.
  - **House style (anti-bloat)** — the soft *"precise, pragmatic, brief"* closer on every agent is
    now a concrete rule: *lead with the verdict · tables/bullets over prose · one line per item · no
    preamble, restating, or praise · prose only when a table can't carry the relation.*
  - **Adaptive 🗺 Design block** — the planner now picks the clearest representation per task instead
    of defaulting to mermaid: one line (obvious change) · data-flow table (transforms) · ASCII
    box-flow (topology — and it renders in the PR, mermaid does not since `feature-research/` is
    gitignored) · mermaid reserved for a genuine 2D graph.
  - **Full plan saved in the PR** — both ship paths (`auto` step 8d + gated `approve-diff`) now embed
    the entire reviewed `plan.md` in a `<details>📋 Full plan</details>` collapse. Since
    `feature-research/` is gitignored and the scratch is deleted at ship, the PR body is now the
    plan's only durable home on GitHub — design, blast radius, 🧯 error handling, scorecard,
    decisions, and both reviews travel with the PR.
  - **PR leads with reviewer essentials** — the visible top of the PR is now the actionable stuff:
    **why · what · 🧪 how to test · ⚙️ setup & requirements** (env vars / new deps / config), then
    open questions + the gate stamp. The long-form plan + audit stay in collapses. The implementer's
    `audit.md` gains a `## ⚙️ Setup & test` section that feeds the visible How-to-test + Setup blocks.
- **0.14.0** — **Auto mode: metric references for every new behavior + bigger quote pools.**
  - **Observability** — the `metrics:` line + state.md gained `panel_model`, `arbiter_trigger`, and
    `override`, so each 0.13.0 behavior is greppable (which model the panel ran on, why the arbiter
    fired, which soft guardrails were relaxed; the migration hard-stop surfaces as
    `outcome=ABORTED:needs-migration`). Extended in all three metrics-emit sites + the REPORT block.
  - **More banner quotes** — every persona's quote pool expanded: auto-mode stages 10 → 14, gated
    commands 20 → 24 (IMPLEMENT/DIFF pools kept byte-identical across `approve-plan.md` + `rework.md`;
    each `(M)` label re-synced to its actual count, which the deterministic selector reads).
- **0.13.0** — **Auto mode: operator override policy + tiered diff panel + always-on arbiter.**
  - **Override policy (operator opt-in)** — auto pushes through the *soft* guardrails to finish the
    task (low planner confidence, scope/runaway caps, sensitive non-migration paths now attach a
    `needs-human` heads-up instead of aborting). **Two hard rules never bend:** never authors/applies
    a migration (hard stop + hand-off), never force-pushes any branch but its own `anderson/auto/*`
    (squash-to-clean on its own branch only). The verification engine is unchanged.
  - **Diff panel model is tier-sized (step 7f)** — trivial/normal panels run on sonnet, hard/critical
    on opus (a missed bug at those tiers has real blast radius).
  - **Arbiter backstops every panel (step 7g)** — the opus arbiter now runs on every split **and**
    every unanimous ship (final sign-off, independent re-review — not a rubber-stamp); only a
    unanimous refute skips it. Closes the gap where a panel that agreed too easily could ship a
    subtly-wrong diff. Gate: PASS iff arbiter `ship`; FAIL on arbiter `fix_first` or unanimous refute.
  - **Docs** — full Commands reference + a full auto-mode pipeline section in the root README; the
    "what replaces the human gates" detail, three-modes section, and override policy in this README.
- **0.12.0** — **Auto mode: PR body leads with the validated plan + multi-repo handling.**
  - **PR body restructured (step 8d)** — opens with the source-ticket link (TaskSpec `source_url`,
    rendered only when present — never fabricated) + a short *reviewed-and-validated* plan summary
    (the `## 🛠 How` groups as terse bullets + a one-line gate-validation stamp); the audit trail,
    residual risks, and `metrics:` line collapse into a `<details>` at the bottom.
  - **Multi-repo (steps 2d + 8e)** — when the task must change repos beyond the current one
    (TaskSpec `repos:`, scope outside the repo, or a sibling repo in project memory / `CLAUDE.md`),
    each repo gets an isolated **git worktree**, its own branch off its latest default, and its own
    cross-linked draft PR (`Companion PRs:` ↔ `Part of <task-id>`), labeled `needs-human`.
  - **Worktree isolation** — a dirty working tree is isolated in a worktree instead of aborting, so
    a run never disturbs in-flight work; worktrees are removed on the terminal path.
  - New additive state fields: `source_url`, `repos`. Version bump `0.11.0 → 0.12.0`.
- **0.11.0** — **Auto mode: adaptive verification (panels + routing + arbiter + CI veto).** Wires
  the four `TODO` stubs in `commands/auto.md` into a difficulty-adaptive harness that targets the
  best success-rate / token / latency balance:
  - **Difficulty routing (step 3b)** — a tier (trivial/normal/hard/critical) is derived from the
    plan Scorecard and re-derived from the actual diff size at the gate (max-only; tier can only
    escalate). A forbidden/dependency-path hit pins it to critical.
  - **Plan gate (step 4)** slimmed to criteria-check + one `plan-reviewer` (skipped for trivial) —
    plan errors are cheap, so rigor is spent at the diff gate.
  - **CI veto first (step 7c)** — real GitHub-Actions gate (push branch, await conclusion; in-tree
    fallback). A red build short-circuits before any reviewer tokens are spent.
  - **Tier-sized blind diff panel (step 7f)** — 1/2/3 `reviewer`s by tier
    (correctness · regressions+security · plan-match), run **in parallel** (each writes its own file
    + returns a verdict, so no shared-state collision), blind to `audit.md` and to each other.
  - **Arbiter on split (step 7g)** — unanimous panel decides directly; a split (or critical tier)
    invokes one opus arbiter that rules on merit and must justify it in a required `## Options
    considered` (+/−) table.
  - **Rework (step 7h)** re-enters straight at the panel with a per-round reset; non-convergence
    bounces to PLAN **once** (forced options table) then escalates to `needs-human`.
  - **Red-for-right-reason (step 5)** — a hollow red (import/syntax/collection error) triggers one
    rewrite, else abort.
  - **Calibration metrics** — every run emits a one-line `metrics:` record for later threshold
    tuning.
  Subagents reused unchanged (lens/posture/model passed via the invocation prompt). New additive
  state fields: `plan_panel`, `diff_panel`, `ci_status`, `ci_conclusion`, `red_reason`, `tier`,
  `reviewers`, `arbiter`, `replan_bounced`. Version bump `0.10.0 → 0.11.0`.
- **0.10.0** — **`/anderson:auto` (experimental non-halting mode).** New orchestrator command runs
  the full plan → RED test → implement → diff-review pipeline end-to-end to a draft PR with no human
  halts. Reuses the four existing subagents unchanged. Enforced this increment: baseline-green
  precondition, run lock per task-id, confidence-gate bail-to-human, test-tamper guard (content-hash
  snapshot at RED), scope/forbidden-path guard (`needs-human` label on dependency changes), thrash
  breaker (open-findings must shrink each rework round), draft-PR-only + branch-only ship. Stubbed
  this increment (explicit `TODO` markers): full 3-lens critic/reviewer panels, real CI-runner veto,
  isolated worktree, red-for-right-reason auto-check. Scheduler gains an additive `mode: auto`
  early-exit guard so hook chaining does not interfere. Spec docs moved into plugin:
  `docs/auto-mode.md` + `docs/auto-mode-handoff.md`. Version bump `0.9.7 → 0.10.0`.
- **0.9.7** — Consolidated the human-facing output into ONE document: plan-review and
  diff-review now write into `plan.md` under `## 🔭 Review` (no separate `diff-review.md`),
  and reviewer divergences are inline colored `<del>`/`<ins>` edits at the change site instead
  of a prepended `## Diverged because` block. The planner template gains a `## 🗺 Design` mermaid
  slot and a `###` logical-grouping convention; `state.md` is now machine-only (not a human doc).
  Terminal color added to the shell surfaces — green stages, red gates — in `bin/banner.sh`,
  `bin/demo.sh`, `bin/feature.sh`, `bin/matrix.sh`, all TTY + `NO_COLOR` gated so logs/CI stay clean.
  CI now FAILS a PR that changes `plugins/anderson/` without bumping the version.
- **0.9.6** — Quote pools doubled to 20 per stage and the modulus is now read dynamically
  from the `"Pool (M):"` label in each banner block, so the formula `(N + stageN + iteration) mod M`
  never needs updating when pools grow. All six pools were expanded: the original 10 aphorisms kept
  verbatim plus 10 Matrix-trilogy lines matched to each stage's persona (THE ARCHITECT, THE
  INTERROGATOR, THE ORACLE, NEO, AGENT SMITH, THE ONE). The IMPLEMENT and DIFF_REVIEW pools are
  kept byte-identical across `approve-plan.md` and `rework.md`. Live-loop only; `bin/*` terminal
  scripts unchanged.
- **0.9.5** — Stage banners switched from a model-printed "pick ONE quote at random" instruction
  to a deterministic, model-computable index: `(N + stageN + iteration) mod M`, where N is the
  character count of the task slug, stageN is a fixed offset per stage (PLAN=1, GRILL=2,
  PLAN\_REVIEW=3, IMPLEMENT=4, DIFF\_REVIEW=5, SHIP=6), and iteration is read fresh from
  `state.md`. Varies by task, stage, and rework pass; mod M over the pool always yields a valid
  index. The unreliable tiebreaker ("recall what you already showed") was dropped — iteration
  covers the only recurrence (rework). `rework.md` gained an explicit `iteration += 1` step so
  rework banners read a post-increment value. Live-loop only; 27 scheduler tests pass.
- **0.9.4** — Finished the banner-reliability fix: added a named per-stage **BANNER RULE**
  invariant (setup first, banner last before the agent, nothing between, never skipped)
  restated at every stage so later banners stop getting dropped; `rework.md` now inlines
  the IMPLEMENT 4/5 + DIFF_REVIEW 5/5 banner blocks (was a stale `/4` reference);
  `/anderson:demo` re-synced to the framed `/5` format and now shows the GRILL 2/5 stage.
  Live-loop only; `bin/*` terminal scripts unchanged.
- **0.9.3** — Stage banners now count **/5** (grill is a step — was a stale /4), and each
  banner prints as the last line *before* its agent deploys, so it sits directly above the
  agent's task line instead of scrolling out of view behind setup output.
- **0.9.2** — Richer terminal intro: `bin/matrix.sh` now holds on the ANDERSON logo,
  shows a line, then runs an accelerated montage of a full run (PLAN → … → SHIP with
  the gates). README landing reworked — pipeline + cast + run-walkthrough collapsed into
  one explicit table, a generic quickstart example, the demo GIF up top, **anderson**
  bolded. (Re-record the GIF with `vhs assets/anderson.tape, on the media branch` to capture the new intro.)
- **0.9.1** — Restyled the stage banners into a tight, framed, persona-led format
  (`╭─ ⌐■-■ STAGE · N/4 · PERSONA · model/effort` + a one-line quote) — dropped the
  repeated wordmark + sparkles that made the old 3-line banner feel busy. Statusline
  persona format matched (`PERSONA · model/effort`). Cosmetic only.
- **0.9.0** — Concise, explicit agent output templates (planner `🎯 What / 🤔 Why / 🛠 How /
  ✅ Decisions`; plan- and diff-review `📊 Evaluation / 💬 Feedback / ⚖️ Verdict`) for scannable,
  minimum-words docs with light emoji headers. New `regrill` plan-review verdict that
  auto-routes `plan_review → grill` (human-gated, resets the verdict to avoid re-bounce).
  `scheduler.py` refactored to an importable `main()` with a 27-test stdlib `unittest` suite.
  Added `LICENSE` (MIT) + README badges/hook/quickstart/persona table. Dogfooded through
  anderson's own pipeline. Agent model/effort unchanged.
- **0.8.1** — Headless parity for ship: `bin/feature.sh --approve-diff` now branches
  (off the default branch, `anderson/<slug>`), commits, pushes, and opens the PR — the
  same guarded flow as the interactive command, but with the commit subject + PR body
  built deterministically from the scratch (no model). Sets a CI fallback git identity
  only if none exists; handles detached HEAD; degrades gracefully without a remote / `gh`.
- **0.8.0** — New **grill** step between plan and plan-review. After the planner drafts
  `plan.md`, anderson interviews you relentlessly about it — one question at a time, down
  each branch of the decision tree, recommending an answer to each, exploring the codebase
  instead of asking when it can — and folds every resolved decision into `plan.md` (under
  `## Decisions`), so the reviewer critiques a hardened plan. Self-contained (no external
  skill); inlined into `/anderson:start`. The scheduler halts at grill as a human checkpoint
  and never auto-skips it. Agent model/effort settings unchanged.
- **0.7.0** — `/anderson:approve-diff` now **ships for real**: it commits the work
  cleanly on a branch (auto-creates `anderson/<slug>` when you're on the default branch,
  else commits on the current branch), pushes, and opens a PR with a generated
  description. Fully guarded — degrades to commit-only + printed PR body when there's no
  remote / no `gh` / not authed; never force-pushes; runs in any repo. Previously it only
  handed you the message. Loop logic + agent model/effort settings unchanged.
- **0.6.3** — Quote pools grew 4 → 10 per stage, with a stronger "pick at random,
  don't reuse one shown this session" instruction so banners stop repeating. The SHIP
  banner gets a dedicated 10-quote ending pool, and the DONE line now states the loop
  has fully stopped (nothing runs in the background). Cosmetic + UX; loop logic unchanged.
- **0.6.2** — Statusline glasses now cycle **colour** each refresh (green → bright
  green → bright cyan → cyan) — closest a plugin can get to a live, "tinkering…"-style
  colour shimmer (refresh-paced, not smooth). Statusline only; honors `NO_COLOR`; loop unchanged.
- **0.6.1** — Stage banners get a glitter accent (`✦` framing the glasses), and the
  GATE prompts now print the resolved command with the real feature slug filled in
  (`/anderson:approve-plan brief-views`, copy-pasteable) instead of a literal `<task>`.
  Cosmetic + UX only; loop logic unchanged. (In-chat banners stay static — true motion
  lives in `bin/statusline.sh` / `bin/matrix.sh`.)
- **0.6.0** — Terminal `bin/matrix.sh` intro (digital rain → glasses/title) and an opt-in
  one-line `bin/statusline.sh` shimmer showing the live stage. Extras only; the loop is unchanged.
- **0.5.1** — Banners render as inline command text (no plugin-script execution), so
  they work for any user without a bash-permission grant; `bin/banner.sh` / `bin/demo.sh` stay for terminal use.
- **0.5.0** — Matrix-flavored stage banners (sunglasses sigil + rotating original,
  mood-matched aphorisms) and a zero-token `/anderson:demo` dry-run of the full pipeline.
- **0.4.0** — Autonomous chaining now actually drives the next turn: the scheduler
  emits real `Stop`/`SubagentStop` hook JSON (`decision:block`+`reason` to chain,
  allow-stop `additionalContext` at gates) instead of discarded stdout, with a
  `stop_hook_active` re-entrancy guard. State parsing is lenient (tolerates `- `
  bullets / `**` bold), and the interactive `/anderson:start` command seeds the exact
  machine-readable STATE block so `/anderson:status` and the scheduler stay in sync.
- **0.3.1** — Gated 4-stage pipeline with per-stage model/effort and two human gates.

Licensed under the [MIT License](LICENSE).
