# anderson

[![ci](https://github.com/amj-lang/anderson/actions/workflows/ci.yml/badge.svg)](https://github.com/amj-lang/anderson/actions/workflows/ci.yml)
[![version](https://img.shields.io/badge/version-0.12.0-blue)](https://github.com/amj-lang/anderson)
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
| **Gate 1 — plan** *(was: human grill + approve)* | criteria-coverage check + **one `plan-reviewer`** (skipped for a trivial tier) | **opus · xhigh** | Refute the plan — find why it fails or misses an acceptance criterion; default to reject if uncertain; fix inline. |
| **Gate 2 — diff** *(was: human review)* | **tier-sized blind `reviewer` panel** — 1 / 2 / 3 by difficulty, run in parallel | **sonnet · xhigh** \* | Each judges ONE lens — *correctness* · *regressions+security* · *plan-match* — from the diff + plan only, **blind** to `audit.md` and to each other; refute, default reject. |
| **Gate 2 — tie-break** | **one `reviewer` as the arbiter** — runs only on a split panel, or always on a critical tier | **opus · xhigh** | Resolve contested findings **on merit, not headcount**; justify the call in a required `## Options considered` (+/−) table. |

\* Panelists take a **sonnet** model override as a cost optimization (effort stays `xhigh` from the
`reviewer` frontmatter); they fall back to the reviewer default **opus · xhigh** when no per-agent
override is available. The arbiter always runs at **opus · xhigh**.

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
- **Plan gate (step 4).** Criteria-coverage check + **one** `plan-reviewer` (skipped entirely for a
  trivial tier). Plan errors are cheap to fix, so the rigor budget is spent at the diff gate.
- **CI veto first (step 7c).** When the repo has GitHub Actions + a remote + `gh`, the branch is
  pushed and the run's conclusion is awaited; a red build fails the gate and **short-circuits before
  any reviewer tokens are spent**. Falls back to the in-tree suite when CI isn't available.
- **Tier-sized blind diff panel (step 7f).** 1 / 2 / 3 `reviewer`s by tier (correctness ·
  regressions+security · plan-match), run **in parallel** (each writes its own file + returns a
  verdict, so no shared-state collision), blind to `audit.md` and to each other.
- **Arbiter on split (step 7g).** A unanimous panel decides directly (the token saver); a split
  invokes one opus arbiter that rules **on merit, not headcount**, and must justify its call in a
  required `## Options considered` (+/−) table. Critical tier always runs the arbiter.
- **Red-for-right-reason (step 5).** The RED test must fail on an *assertion*; an import/syntax/
  collection error (a hollow red) triggers one bounded rewrite, then aborts.
- **Calibration metrics.** Every run emits a one-line `metrics:` record (tier · reviewers · arbiter ·
  rounds · ci · outcome) to the PR + report, so the thresholds can be tuned from real outcomes.
- **PR body leads with the validated plan.** The draft PR opens with the source-ticket link (from
  the TaskSpec `source_url`, when present) + a short reviewed-and-validated plan summary; the audit
  trail and metrics collapse to the bottom.
- **Multi-repo.** When the task must change other repos (TaskSpec `repos:`, scope spilling outside the
  repo, or a sibling repo in project memory / `CLAUDE.md`), each repo gets an isolated **git worktree**,
  its own branch, and its own cross-linked draft PR (labeled `needs-human`). A dirty tree is isolated
  in a worktree rather than aborting.

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

![anderson — digital-rain intro](../../assets/anderson-demo.gif)

## Personas

| Persona          | Stage         | Role                                   | Model / effort |
|------------------|---------------|----------------------------------------|----------------|
| THE ARCHITECT    | `plan`        | writes the plan                        | opus / high    |
| THE INTERROGATOR | `grill`       | you — relentless one-at-a-time Q&A     | — (human)      |
| THE ORACLE       | `plan_review` | edits the plan inline + appends review to `## 🔭 Review` | opus / xhigh   |
| NEO              | `implement`   | executes the approved plan             | sonnet / medium|
| AGENT SMITH      | `diff_review` | read-only diff review                  | opus / xhigh   |
| THE ONE          | `done`        | shipped — commit + PR                  | — (terminal)   |

## Pipeline

```
plan ─▶ grill ─▶ plan_review ──[ YOU ]──▶ implement ──▶ diff_review ──[ YOU ]──▶ done
high   [ YOU ]   xhigh (edits)            medium        xhigh (read-only)
                                    ▲              │ fix_first
                                    └──────────────┘
```

| Stage        | Agent          | Model  | Effort | Gate  | Does                                  |
|--------------|----------------|--------|--------|-------|---------------------------------------|
| plan         | `planner`      | opus   | high   | —     | writes `plan.md` + blast radius + scorecard |
| grill        | *(you)*        | —      | —      | human | relentless one-at-a-time Q&A on the plan, folds decisions into `plan.md` — no subagent |
| plan_review  | `plan-reviewer`| opus   | xhigh  | human | **edits** `plan.md` inline + appends review to `## 🔭 Review`; re-scores + checks blast radius; verdict `ship`/`fix_first`/`regrill` |
| implement    | `implementer`  | sonnet | medium | —     | writes `audit.md`                     |
| diff_review  | `reviewer`     | opus   | xhigh  | human | diff review appended to `plan.md` `## 🔭 Review` |

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
| `/anderson:start <slug> <goal>` | **Entry point** (gated mode). Seeds `state.md`, plans, **grills you** one question at a time, then plan-reviews (edits the plan inline). | Halts at 🛑 **Gate 1**. Read `plan.md` → `## 🔭 Review` + `## 💥 Blast radius` + `## 📈 Scorecard`. |
| `/anderson:approve-plan <slug>` | Pass **Gate 1**: implement + independent diff-review. | Code + `audit.md` written, review appended. Halts at 🛑 **Gate 2**. Read `## 🔭 Review` AND the diff. |
| `/anderson:approve-diff <slug>` | Pass **Gate 2** = **SHIP for real**: branch `anderson/<slug>` + commit + push + open PR (all guarded), then clean scratch. | Branch + PR URL, or a local-commit fallback if no remote/`gh`. **Never force-pushes.** |
| `/anderson:rework <slug>` | Diff review said `fix_first` — loop the implementer on the "Still open" blockers only, then re-review. | Back to 🛑 **Gate 2**. Bounded by `max_iterations`. |
| `/anderson:status <slug>` | Dashboard / sanity check. | Current stage, next agent + model/effort, both verdicts, iteration vs max, and the `CLAUDE_CODE_SUBAGENT_MODEL` override check. Read-only. |
| `/anderson:demo` | Zero-token dry-run of the whole pipeline. | All stage banners + both gate lines + ship banner. No agents, no files, no tokens. |
| `/anderson:auto <id> <title> [body\|@file]` | **Autonomous mode** — no gates: plan → plan-gate → RED test → implement → CI-veto + panel diff-gate → **draft PR**. | Terminal SHIP (draft PR) or abort + `report.md`. Review the PR — auto mode is experimental. |

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
plan-reviewer=purple, implementer=green, reviewer=orange), so you can tell at a glance
which one is working.

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

`plan.md` carries mandatory sections beyond the How narrative: a **`## 💥 Blast radius`** table (planner traces all dependents/callers/siblings/tests/docs before finalizing; reviewer hard-checks it, blocking on blank cells or missed in-scope sites), a **`## 📈 Scorecard`** (7 dimensions — Risk, Horizontality, Testability, Reversibility, Confidence, Coupling, Observability — with Planner and Reviewer columns in one table; gaps ≥ 3 reconciled inline; Risk ≥ 8 or Confidence ≤ 3 blocks `ship`), and a **`## 🔭 Review`** section (last, reserved — the plan-reviewer appends its structured report here after making inline edits, and the diff-reviewer appends its diff review here; replaces the former separate `diff-review.md` and `## Diverged because` block). The scorecard is echoed verbatim into `audit.md` by the implementer.

## Models & effort — what runs where, and how to verify

Each agent declares its own `model` + `effort` in frontmatter, and these switch
automatically per stage (planner opus/high, plan-reviewer opus/xhigh, implementer
sonnet/medium, reviewer opus/xhigh). Resolution order is: `CLAUDE_CODE_SUBAGENT_MODEL`
env var → per-invocation override → **agent frontmatter** → main session.

**The gotcha:** if `CLAUDE_CODE_SUBAGENT_MODEL` is set, it overrides every agent's
frontmatter — your implementer would silently run on whatever that env says, not
Sonnet. `/anderson:status` prints this for you; or check directly:

```
echo "${CLAUDE_CODE_SUBAGENT_MODEL:-<unset, good>}"
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
   PR body (what changed + why, the review verdict, files touched, test status) from
   the scratch — *before* it deletes anything.
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

Two optional flourishes in `bin/` — run them in a real terminal (the in-loop banners are plain text and don't animate):

- **`bash bin/matrix.sh`** — green digital-rain intro that resolves into the `⌐■-■ A N D E R S O N` logo. Honors `NO_COLOR` / non-TTY (prints a clean static frame). Tunables: `MATRIX_DELAY`, `MATRIX_FRAMES`. Great for a demo GIF.
- **`bin/statusline.sh`** — a one-line status bar with the live loop stage + a calm shimmer (glasses + rain cycle ~1/sec). Opt-in; add to `settings.json` with an absolute path (this replaces any existing statusline):
  ```
  "statusLine": { "type": "command", "command": "bash /ABS/PATH/plugins/anderson/bin/statusline.sh" }
  ```

## Changelog

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
  bolded. (Re-record the GIF with `vhs assets/anderson.tape` to capture the new intro.)
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
