---
description: "Quick-reference card: all anderson commands, arguments, gates, and the --fable flag. One-shot display, reads nothing."
---
Print the reference card below exactly as written — no tools, no state reads, no
additions, no commentary before or after. It is static help, not a dashboard
(that is `/anderson:status <slug>`).

```
ANDERSON — gated build loop: plan → grill → plan-review 🛑 → implement → diff-review 🛑 → ship

  /anderson:start <slug> <goal> [--fable]              begin gated task; halts at Gate 1 (plan)
  /anderson:approve-plan <slug>                        pass Gate 1 → implement + diff-review; halts at Gate 2
  /anderson:rework <slug>                              loop implementer on blocking findings → re-review
  /anderson:approve-diff <slug>                        pass Gate 2 → commit, push, PR (guarded)
  /anderson:auto <id> <title> [body|@file] [--fable]   no gates → draft PR (experimental)
  /anderson:status <slug>                              dashboard: stage, verdicts, next agent/model
  /anderson:demo                                       preview pipeline UX, no agents, no tokens
  /anderson:help                                       this card

  --fable   run the critique gates (plan-review, diff-review/arbiter) on Fable instead of
            Opus. Generative stages (planner, implementer) stay Opus/Sonnet. Set once at
            start/auto, persists in state.md across approve-plan/rework. Place at the end.

  state:    feature-research/<slug>/{state.md,plan.md,audit.md} — every command reads state.md,
            so a running flow also answers plain text: "approved, go" / "ship it" / "rework".
```
