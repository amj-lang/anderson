---
description: "Approve the plan, run implement then diff-review, then halt."
argument-hint: <task-slug>
allowed-tools: Bash(bash:*)
---
Task slug = "$ARGUMENTS". In state.md set plan_verdict=ship, gate=none, iteration += 1.
If iteration > max_iterations, print `■ EXIT · hit max_iterations` and STOP.

1. Show the IMPLEMENT banner:
   !`bash "${CLAUDE_PLUGIN_ROOT}/bin/banner.sh" implement`
   Set stage=implement. Invoke the **implementer** subagent: execute plan.md; on
   a rework loop fix only "Still open". Writes audit.md. Set stage=diff_review.
2. Show the DIFF-REVIEW banner:
   !`bash "${CLAUDE_PLUGIN_ROOT}/bin/banner.sh" diff_review`
   Invoke the **reviewer** subagent → writes diff-review.md, sets diff_verdict.
3. Print and STOP:
   `■ GATE 2 · awaiting you. Read feature-research/<task>/diff-review.md AND the actual diff (verdict=<diff_verdict>). Then /anderson:approve-diff <task> to ship, or /anderson:rework <task>.`
   Halt is unconditional even on a ship verdict.
