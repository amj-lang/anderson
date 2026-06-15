---
description: "Loop the implementer on the checker's blocking findings, then diff-review and halt."
argument-hint: <task-slug>
---
Task slug = "$ARGUMENTS". Blocking findings are already in state.md "Still open".
Run exactly the implement → diff_review → halt sequence from approve-plan
(printing the same stage 3/4 and 4/4 banners), incrementing iteration and
stopping if it exceeds max_iterations.
