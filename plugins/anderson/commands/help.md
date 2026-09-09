---
description: "Quick-reference card: all anderson commands, arguments, gates, and the --opus flag. One-shot display, reads nothing."
---
Print the reference card below exactly as written — no tools, no state reads, no
additions, no commentary before or after. It is static help, not a dashboard
(that is `/anderson:status <slug>`).

```
ANDERSON — gated build loop: plan → grill → plan-review 🛑 → implement → diff-review 🛑 → ship

  /anderson:start <slug> <goal> [--opus]               begin gated task; halts at Gate 1 (plan)
  /anderson:approve-plan <slug>                        pass Gate 1 → implement + diff-review; halts at Gate 2
  /anderson:rework <slug>                              loop implementer on blocking findings → re-review
  /anderson:approve-diff <slug>                        pass Gate 2 → commit, push, PR (guarded)
  /anderson:auto <id> <title> [body|@file] [--opus]    no gates → draft PR (experimental)
  /anderson:status <slug>                              dashboard: stage, verdicts, next agent/model
  /anderson:demo                                       preview pipeline UX, no agents, no tokens
  /anderson:fleet                                      THE OPERATOR: launch card for the cross-repo session monitor
  /anderson:help                                       this card

  --opus    run the critique gates (plan-review, diff-review/arbiter) on Opus instead of
            the default Fable. ESCAPE VALVE, not an upgrade: Fable outscores Opus at every
            effort level on fewer tokens, so reach for this only when the Fable budget is
            spent. Generative stages (planner, implementer) stay Opus/Sonnet. Set once at
            start/auto, persists in state.md across approve-plan/rework. Place at the end.

  tier:     trivial|normal|hard|critical, derived from the plan Scorecard, re-tiered on the
            real diff (escalates only). Drives review effort — plan critique runs one rung
            above the diff critique, capped at xhigh; trivial skips plan-review entirely.
            See docs/tiering.md.

  slug:     a pasted branch name works (user/ar-123-title): dir = last segment, ship branch = the slug.
  state:    feature-research/<slug>/{state.md,plan.md,audit.md} — every command reads state.md,
            so a running flow also answers plain text: "approved, go" / "ship it" / "rework".
```
