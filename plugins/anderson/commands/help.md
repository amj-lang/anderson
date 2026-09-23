---
description: "Quick-reference card: all anderson commands, arguments, gates, and tiers. One-shot display, reads nothing."
---
Print the reference card below exactly as written — no tools, no state reads, no
additions, no commentary before or after. It is static help, not a dashboard
(that is `/anderson:status <slug>`).

```
ANDERSON — gated build loop: plan → grill → plan-review 🛑 → implement → [repair] → diff-review 🛑 → ship
                              [repair] fires only when tests are red

  /anderson:start <slug> <goal>                        begin gated task; halts at Gate 1 (plan)
  /anderson:approve-plan <slug>                        pass Gate 1 → implement + diff-review; halts at Gate 2
  /anderson:rework <slug>                              loop implementer on blocking findings → re-review
  /anderson:approve-diff <slug>                        pass Gate 2 → commit, push, PR (guarded)
  /anderson:auto <id> <title> [body|@file]             no gates → draft PR (experimental)
  /anderson:status <slug>                              dashboard: stage, verdicts, next agent/model
  /anderson:demo                                       preview pipeline UX, no agents, no tokens
  /anderson:fleet                                      THE OPERATOR: launch card for the cross-repo session monitor
  /anderson:help                                       this card

  models:   planner opus/medium · plan-review opus (a rung above the planner) · implementer
            sonnet/medium · repair opus/high · diff-review/arbiter opus. No flags, no Fable.

  repair:   tests red? the implementer gets ONE try, then TRINITY (test-fixer, ALWAYS opus/high,
            never tiered) root-causes it: reproduce, flake-check, name the cause, smallest
            fix, full suite green. It may never weaken, skip or delete a test. Verdicts: fixed ·
            flake · replan · needs-human; budget 2 rounds, then it escalates to you.

  tier:     trivial|normal|hard|critical, derived from the plan Scorecard, re-tiered on the
            real diff (escalates only). Drives review effort — plan-review high (xhigh at
            critical), diff-review/arbiter high (xhigh at hard/critical).
            See docs/tiering.md.

  slug:     a pasted branch name works (user/ar-123-title): dir = last segment, ship branch = the slug.
  state:    feature-research/<slug>/{state.md,plan.md,audit.md} — every command reads state.md,
            so a running flow also answers plain text: "approved, go" / "ship it" / "rework".
```
