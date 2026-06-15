# anderson

A gated maker/checker pipeline for Claude Code, packaged as a plugin so it works
in **every repo** and installs for your **whole team** from one source.

```
plan ──▶ plan_review ──[ YOU ]──▶ implement ──▶ diff_review ──[ YOU ]──▶ done
high      xhigh (edits)            medium        xhigh (read-only)
                                     ▲              │ fix_first
                                     └──────────────┘
```

| Stage        | Agent          | Model  | Effort | Gate  | Does                                  |
|--------------|----------------|--------|--------|-------|---------------------------------------|
| plan         | `planner`      | opus   | high   | —     | writes `plan.md`                      |
| plan_review  | `plan-reviewer`| opus   | xhigh  | human | **edits** `plan.md` + `## Diverged because`, keeps `plan.orig.md` |
| implement    | `implementer`  | sonnet | medium | —     | writes `audit.md`                     |
| diff_review  | `reviewer`     | opus   | xhigh  | human | **read-only** diff review → `diff-review.md` |

The agents are **self-contained** — the implementer/reviewer logic is inlined, so
there is no external skill to install. Per-stage `model` + `effort` switch
automatically as the pipeline routes to each agent. Both human gates halt
unconditionally, even on a `ship` verdict.

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

**Local marketplace (current — no git remote needed).** Point Claude Code at the
**marketplace root** — the dir that contains `.claude-plugin/marketplace.json`
(this repo's top level), substituting your real absolute path:

```
/plugin marketplace add /absolute/path/to/anderson
/plugin install anderson@dodge-this
```

**From a git remote (team / v1+).** Once the repo is pushed (planned for v1), you
and teammates run the same two lines against the remote instead:

```
/plugin marketplace add <you>/anderson
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
/plugin marketplace add <you>/anderson
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

```
/anderson               brief-views  normalize briefs_table.views[] into brief_views_table
            # START. plan + plan-review, then halts. Read plan.md → "## Diverged because".
/anderson:approve-plan  brief-views
            # implement + diff-review, then halts. Read diff-review.md AND the diff.
/anderson:approve-diff  brief-views     # ship (summarizes to commit, removes scratch)
/anderson:rework        brief-views     # loop implement on the checker's blocking findings
/anderson:status        brief-views     # dashboard + model-override check
```

The reliable, unambiguous form is the **fully-qualified** `/anderson:<command>` —
that's how they register: `/anderson:approve-plan`, `:approve-diff`, `:rework`,
`:status` (start is `/anderson`, which may also resolve bare since the file
matches the plugin name). If a bare `/approve-plan` isn't found, add the
`/anderson:` prefix. None of these are mandatory anyway: once a flow is running
you can drive every gate in plain text — "approved, go" / "ship it" / "rework the
blockers" — since the agents read the same `state.md`.

**What you see while it runs.** Each command prints a one-line banner before it
dispatches, e.g. `▶ [anderson 3/4 · IMPLEMENT] agent=implementer ·
model=sonnet · effort=medium · executing plan.md`, and the four agents are
colour-coded in the subagent panel — planner=blue, plan-reviewer=purple,
implementer=green, reviewer=orange — so you can tell at a glance which one is
working.

State persists in `feature-research/<task>/state.md` in the current repo, so you
can stop at a gate and resume later.

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
/ 20) so it composes with CI or a Makefile. Add it to PATH or call directly:

```
./bin/feature.sh start brief-views "normalize views[] into brief_views_table"
./bin/feature.sh --approve-plan brief-views
./bin/feature.sh --approve-diff brief-views   # or --rework
```

## Optional — autonomous between-gate chaining

`hooks/hooks.json` registers a `SubagentStop`/`Stop` scheduler that auto-advances
the state and chains plan→plan_review and implement→diff_review without you
issuing each command, still halting at the two human gates. It's on by default in
the plugin; remove the `hooks/` directory if you'd rather drive every step
explicitly.

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

The durable record is your **git history**, not the scratch files. So on
`/anderson:approve-diff` the loop hands you a ready commit/PR message
(`<goal> (review: ship · N blocking resolved)`) and **removes
`feature-research/<task>/`**. It does not commit for you — you commit. The
scratch dir is also gitignored on start, so the plan/audit/review files never
pollute the repo. Nothing stale is left behind.

## Token notes

Each agent runs in its own context window and gets only its own prompt — verbose
work stays out of your main context. State lives on disk, so per-iteration context
stays flat. Keep agent prompts byte-stable so Claude Code caches the prefix (cache
reads ≈ 0.1× input); don't inject the date/iteration into a prompt prefix — that's
what the on-disk state is for.

## Changelog

- **0.4.0** — Autonomous chaining now actually drives the next turn: the scheduler
  emits real `Stop`/`SubagentStop` hook JSON (`decision:block`+`reason` to chain,
  allow-stop `additionalContext` at gates) instead of discarded stdout, with a
  `stop_hook_active` re-entrancy guard. State parsing is lenient (tolerates `- `
  bullets / `**` bold), and the interactive `/anderson` command seeds the exact
  machine-readable STATE block so `/anderson:status` and the scheduler stay in sync.
- **0.3.1** — Gated 4-stage pipeline with per-stage model/effort and two human gates.
