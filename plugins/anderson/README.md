# anderson

[![ci](https://github.com/amj-lang/anderson/actions/workflows/ci.yml/badge.svg)](https://github.com/amj-lang/anderson/actions/workflows/ci.yml)
[![version](https://img.shields.io/badge/version-0.72.1-blue)](https://github.com/amj-lang/anderson)
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

Living spec: `plugins/anderson/docs/auto-mode.md`.

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
| SERAPH           | `plan_review` + `diff_review` | security lens seat, summoned by the plan and the diff | opus / high  |
| NIOBE            | `plan_review` + `diff_review` | performance lens seat, summoned by the plan and the diff | opus / medium (high from HARD) |
| THE MEROVINGIAN  | `diff_review` | dead-code lens seat: what this diff orphaned | opus / medium (high from HARD) |
| THE ONE          | `done`        | shipped — commit + PR                  | — (terminal)   |

SERAPH, NIOBE and THE MEROVINGIAN are not agents of their own: each is the `reviewer` agent in a
lens seat. `bin/crew.py` summons them from what the diff touches (paths and changed lines, no
model call): SERAPH for auth, sessions, API routes, input parsing, SQL/shell/HTML building,
secrets, dependencies, and always from HARD up; NIOBE for queries, loops over I/O, React effects,
caching; THE MEROVINGIAN whenever the diff changes or removes existing code. They review blind
into their own files first, then AGENT SMITH (or the auto arbiter) rules on their findings.
SERAPH and NIOBE also sit at plan review (`crew.py --plan`, routed from the plan's Files touched and
text), before THE ORACLE, which folds each confirmed finding into plan.md: a design flaw costs one
plan edit there instead of a rework round after the code exists. THE MEROVINGIAN waits for the diff.
The planner can add a seat the rules would miss with a `**Crew hint:**` line in plan.md (an auth check
inside business logic, a hot path behind a helper); hints only add, they never remove a rule's pick.

### Run log

Every run that ends (shipped, aborted, or out of iterations) appends one JSON line to
`~/.claude/anderson/runs.jsonl` (override with `ANDERSON_RUNLOG`): the STATE block, the crew and each
seat's confirmed/raised tally, the outcome, the PR. It stays on your machine; nothing sends it
anywhere. `python3 bin/runlog.py --summary` adds it up (illustrative numbers):

```
runs 23 · aborted 2 · shipped 21
tiers critical 1 · hard 6 · normal 12 · trivial 4
rework rounds avg 0.6
critical  runs   1 · tokens med 910k · time med 41m · rework 1/1
hard      runs   6 · tokens med 640k · time med 27m · rework 3/6
normal    runs  12 · tokens med 310k · time med 12m · rework 2/12
trivial   runs   4 · tokens med 80k · time med 3m · rework 0/4
SERAPH       seated   9 · confirmed 4/6 raised
NIOBE        seated   5 · confirmed 0/2 raised
MEROVINGIAN  seated  17 · confirmed 11/14 raised
```

Tokens and time come from a ledger the band writes per subagent seat (`feature-research/<task>/cost.jsonl`, folded into the run line when it ends); older runs, or runs without the band, print `n/a`. Main-loop tokens are not attributed to a stage.

A seat that is seated often and confirmed rarely is a pattern to tighten in `bin/crew.py`; a bug that
shipped without the seat that should have caught it is a pattern to widen.

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

**Slicing.** The planner writes `**Size:** ~<N>k tokens → <n> slice(s)` under the Scorecard
(implement-stage estimate ÷ 250k: slicing costs a re-plan and review per slice, so only big jobs
pay for it). With n ≥ 2 it plans slice 1 only and adds `## 🔪 Slices` (slices, depends-on, the
contracts between them). Gate 1 then asks `split? (y/n)`: `y` writes
`feature-research/<task>.slices.md` (shared branch, PR, one row per slice), posts one comment on a
Linear parent (its description never touched) and approves slice 1; `n` is the plain Gate 1.
Slices run in order and stack on ONE branch: slice 1 opens a draft PR, each later slice adds a
commit and a `## ✂ Slice <k>` section to it, the last one marks it ready. `/anderson:start <branch>`
picks up the next `todo` slice in slice mode (planner scoped to the slice, grill skips settled
decisions). `/anderson:approve-diff` runs a ripple check against the contracts, then offers the
next slice. `/anderson:auto` does not slice. `runlog.py --summary` buckets first-review blocking
findings by implement tokens, so the 250k line can be checked against real runs.

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
| `/anderson:proto <what> [--task <slug>]` | A visual question words won't settle (a screen, a terminal row). | THE CONSTRUCT (`prototyper`, sonnet/medium) builds 2-3 variants that differ on layout, hierarchy or interaction: ASCII for terminal UIs (driving the repo's own renderer when it has one), self-contained HTML for web (using the repo's tokens). You pick, mix, or say `again <steer>`. Inside a task the pick lands in `design/` and becomes a `source: design` criterion. The grill offers it on every 🎨 question. |
| `/anderson:demo` | Zero-token dry-run of the whole pipeline. | The crew band at every stage + both gate cards. No agents, no files, no tokens. |
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

**What you see while it runs.** The crew band, just above the prompt: stage dots, one
box per running agent (persona, model/effort, what it does right now, its verdict when
done), and `your turn ▸ <command>` at a gate. `/anderson:demo` shows every frame.

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
orchestrator (reads state, dispatches) — it does no heavy
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
the plugin; remove the `SubagentStop`/`Stop` scheduler entries from `hooks/hooks.json`
if you'd rather drive every step explicitly (deleting `hooks/` would also kill the band,
the fleet events and the ping).

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

Optional flourishes in `bin/` — run them in a real terminal:

- **`fleet`** — **THE OPERATOR**, the cross-repo fleet monitor and where work starts. Install once
  with `/anderson:fleet` (writes a `fleet` shim to `~/.local/bin` that resolves the newest installed
  anderson at run time, so plugin updates never break it), then in any terminal tab: `fleet`. It runs
  right there. `fleet --tmux` (a tmux session named `fleet`), `--pane` / `--window` (inside tmux) are
  there if you want them.

  On top, every live Claude Code session on the machine, ringing first: repo · **task** (the anderson
  task, else Claude's own title for the session, the one on its tab) · **pipeline** (persona glyph,
  stage `n/max` and tier when the session runs anderson: ▲ plan, ◇ grill, ◎ plan review, ● implement,
  ✚ repair, ▣ diff review, ★ shipped; tier `triv` · `normal` · `HARD` · `CRITICAL`) · **now**
  (`▶ Bash pytest -q`, `☎ ring 12m` = waits on you, `☎ permission Bash`, `☎ question`, `✝ sentinel` =
  the process died, `⟲` = rework loop) · context bar · age. Sessions you closed, and ones dead for over
  an hour, fold into one `dead (n)` line. Below, the repos of the workspace fleet was launched from
  (`dir/repo` when nested), each with its live agent count: the places `N` starts a new agent, which
  gets selected as soon as it shows up. Runs **outside** Claude (python stdlib curses, zero tokens).

  **When it rings.** The plugin's hooks are the truth: a Stop, a permission prompt or a question
  (`AskUserQuestion`, `ExitPlanMode`) means the session waits on you; every prompt and tool event means
  it is working. A ring alerts once, 5 s after it starts, so a turn that carries on by itself (a Stop
  the scheduler blocks to chain the next stage) never rings. A turn you interrupted with Esc fires no
  Stop, so it rings after 15 silent minutes. No alert while that session's own tab is in front of you.

  Keys: `↑↓` tune · `⏎` / `1`-`9` **jack in**: bring that session's tab to the front, in whichever app
  owns it (Ghostty, found exactly by tty; iTerm2 / Terminal.app; the tmux pane; an IDE is brought
  forward). On a sentinel it opens a new tab running `claude --resume`; on a repo row it opens the
  spawn box · `N` **new agent**: a prompt box, then `p` / `a` / `A` launches a bare claude /
  `/anderson:start` / `/anderson:auto` in a new tab of its own (on a session row: its repo). A repo
  parked on a feature branch gets a worktree (`.worktrees/<task>` on `anderson/<task>`, cut from the
  default branch) so the work in progress there is never touched · `w` jump to the longest-waiting
  ring · `o` read plan.md / audit.md right in fleet (then the code diff, at diff review) · `r` kill
  (asks first) · `b` hide a row or a repo (the process is left alone) · `h` show hidden · `space` fold
  the repo list · `m` ring sound on/off, for every fleet you have open · `/` filter · `?` manual · `q`.

  **Getting back.** fleet titles its tab `⌐■-■ fleet`. `fleet --focus` brings that tab to the front
  from anywhere: bind it to a global hotkey (Raycast, Shortcuts, skhd) and it is the way back after a
  jack in. With `--notify` and `terminal-notifier`, clicking a ring banner jumps straight to that
  session's tab (`fleet --jack <session id>`).

### What fleet needs

Required: **python3** (stdlib only, no pip) and the tools every macOS / Linux box already has (`ps`, `lsof`,
`less`; `afplay` / `osascript` on macOS). Everything else is optional and `fleet install` tells you what is
missing; `fleet install --extras` installs the first two, `--with-tmux` the third:

| tool | for | install |
|---|---|---|
| `glow` | `o` renders plan.md / audit.md as real markdown (else `less` with a light colouring) | `brew install glow` · `dnf install glow` · apt: [charm repo](https://github.com/charmbracelet/glow#installation) |
| `terminal-notifier` | macOS desktop banners (`--notify`): reliable, silent (the ring is `m`'s job), a click jumps to the session | `brew install terminal-notifier` |
| `tmux` | `fleet --pane` / `--window` / `--tmux`, and ⏎ jack-in by pane | `brew install tmux` · `apt install tmux` · `dnf install tmux` |
| `notify-send`, `paplay`/`aplay` | Linux: banners, ring sound | usually there (`libnotify`, PulseAudio / ALSA) |

`/anderson:fleet --extras` and `/anderson:fleet --with-tmux` pass the flags through.

### Keeping fleet current

`fleet update` refreshes the marketplace, updates the anderson plugin through the `claude` CLI, and
prints what it moved from and to; restart Claude Code to apply it. The `~/.local/bin` shim resolves the
newest cached version every time it runs, so it never needs re-installing after an update. Without the
`claude` CLI on PATH, run `/plugin update anderson` from inside Claude Code instead.

  **Settings**, saved in `~/.claude/fleet/prefs.json`: `--plain` swaps the Matrix lingo
  (`zion · 3 jacked in · 1 ringing · 0 sentinels`) for plain English (`fleet · 3 live · 1 waiting ·
  0 dead`); `--calm` stops the motion (header rain, ringing rows breathing); `--ring NAME` picks the
  ring sound (phone · snare · hitech · freeze · blip · rift · jump, or your own `.wav` in
  `~/.claude/fleet/sounds/`) and turns sound on; `--notify` turns desktop banners on; `--cost` shows
  the api$ column on a subscription. One-offs: `--no-intro` skips the boot rain, `--once` prints one
  plain frame, `--ascii` uses single-byte glyphs, `--selftest` proves every line equals the terminal
  width at 40..300 columns (wide/CJK/accents safe). Only the frame lines that changed are
  repainted, so an idle monitor emits nothing.

  Data, richest first, each optional (the view degrades, never breaks):
  1. **no setup**: `ps` + `lsof` find running `claude` processes; the transcript tail
     (`~/.claude/projects/<cwd>/<sid>.jsonl`) gives last tool / last words / context tokens; the
     repo's `feature-research/*/state.md` gives stage → persona.
  2. **this plugin's hooks** (`hooks/fleet_event.py` on SessionStart / UserPromptSubmit /
     PreToolUse / PostToolUse / Notification / Stop / SessionEnd) write
     `~/.claude/fleet/<sid>.event.json`: the exact waiting-on-you vs working signal, permission
     prompts included, and when the wait began.
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

## Credits

The grill and the token slicing come from [Matt Pocock](https://github.com/mattpocock/skills) (`grill-me`, `to-tickets`, and throwaway prototypes for questions a grill can't settle). anderson adapts them to its gated loop.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
