---
description: "Approve the plan, run implement then diff-review, then halt."
argument-hint: <task-slug>
---
Task slug = "$ARGUMENTS". In state.md set plan_verdict=ship, gate=none, iteration += 1.
If iteration > max_iterations, print `■ EXIT · hit max_iterations` and STOP.

1. Print: `▶ [claude-loop 3/4 · IMPLEMENT] agent=implementer · model=sonnet · effort=medium · executing plan.md`
   Set stage=implement. Invoke the **implementer** subagent: execute plan.md; on
   a rework loop fix only "Still open". Writes audit.md. Set stage=diff_review.
2. Print: `▶ [claude-loop 4/4 · DIFF-REVIEW] agent=reviewer · model=opus · effort=xhigh · read-only diff review`
   Invoke the **reviewer** subagent → writes diff-review.md, sets diff_verdict.
3. Print and STOP:
   `■ GATE 2 · awaiting you. Read feature-research/<task>/diff-review.md AND the actual diff (verdict=<diff_verdict>). Then /claude-loop:approve-diff <task> to ship, or /claude-loop:rework <task>.`
   Halt is unconditional even on a ship verdict.
