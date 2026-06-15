# anderson

A gated maker/checker build loop for Claude Code, packaged as a plugin. It runs one
task through **plan → plan-review → [you] → implement → diff-review → [you]**, using
four role-specialized subagents (each with its own model + effort) and two human
gates that halt unconditionally — because *green ≠ understood*.

> This is the **marketplace repo**. The plugin itself lives in
> [`plugins/anderson/`](plugins/anderson) — see its
> [README](plugins/anderson/README.md) for the full docs (model/effort resolution,
> the headless runner, autonomous between-gate chaining, token notes).

## Pipeline

```
plan ──▶ plan_review ──[ YOU ]──▶ implement ──▶ diff_review ──[ YOU ]──▶ done
high      xhigh (edits)            medium        xhigh (read-only)
                                     ▲              │ fix_first
                                     └──────────────┘
```

| Stage        | Agent          | Model  | Effort | Gate  | Does                                   |
|--------------|----------------|--------|--------|-------|----------------------------------------|
| plan         | `planner`      | opus   | high   | —     | writes `plan.md`                       |
| plan_review  | `plan-reviewer`| opus   | xhigh  | human | **edits** `plan.md` + `## Diverged because` |
| implement    | `implementer`  | sonnet | medium | —     | writes `audit.md`                      |
| diff_review  | `reviewer`     | opus   | xhigh  | human | **read-only** diff review              |

## Install

```
/plugin marketplace add amj-lang/anderson
/plugin install anderson@dodge-this
```

Restart Claude Code fully (not just `/reload`), then drive it:

| Action | Command |
|--------|---------|
| **Start** (plan + plan-review) | `/anderson:start <task-slug> <goal>` |
| Approve plan → implement + diff-review | `/anderson:approve-plan <task>` |
| Ship | `/anderson:approve-diff <task>` |
| Rework on the checker's blockers | `/anderson:rework <task>` |
| Status dashboard | `/anderson:status <task>` |

Commands are namespaced `/anderson:<command>` (bare `/anderson` does not resolve).
Once a flow is running you can also drive every gate in plain English —
"approved, go" / "ship it" / "rework the blockers".

## Layout

```
anderson/                              <- marketplace root: add THIS as the marketplace
├── .claude-plugin/marketplace.json    <- handle: dodge-this · source: ./plugins/anderson
└── plugins/anderson/                  <- the plugin
    ├── .claude-plugin/plugin.json
    └── agents/  commands/  hooks/  bin/  README.md
```

Plugin: **`anderson`** · marketplace handle: **`dodge-this`** · install:
**`anderson@dodge-this`**.

## Updating

Bump `version` in both `plugins/anderson/.claude-plugin/plugin.json` and
`.claude-plugin/marketplace.json` (keep them in sync), push, then users run
`/plugin marketplace update dodge-this` + reinstall + restart.
