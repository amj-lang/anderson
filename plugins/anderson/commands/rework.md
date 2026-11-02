---
description: "Loop the implementer on the checker's blocking findings, then diff-review and halt."
argument-hint: <task-slug>
---
Task slug = "$ARGUMENTS". Blocking findings are already in state.md "Still open".
Read `${CLAUDE_PLUGIN_ROOT}/commands/approve-plan.md` and run it top to bottom for this slug
(iteration += 1 and the max_iterations exit, re-tier, TIER LINE, implement, TRINITY on red,
crew + diff review, GATE 2 card, halt). This is its rework loop: the implementer fixes ONLY
"Still open", and a round that leaves the tests RED goes to TRINITY (its step 1b), never back to
the implementer.
