---
description: "Ship the task after your diff review: summarize to the commit, then remove the scratch dir."
argument-hint: <task-slug>
allowed-tools: Bash(rm:*), Bash(echo:*), Bash(cat:*)
---
Task slug = "$ARGUMENTS". In state.md set diff_verdict=ship, stage=done.

1. Build a one-line summary from the audit's "Files changed" + the diff-review
   verdict, and present it as a ready-to-use commit/PR message, e.g.:
   `<goal>  (review: ship · <N> blocking resolved)`
   Do NOT commit for me — I'll commit. Just hand me the message.
2. Remove the disposable scratch: `rm -rf "feature-research/$ARGUMENTS"`.
   (The git history + commit message are the durable record; the plan/audit/
   review files were only scaffolding the agents passed between each other.)
3. Print: `✓ [claude-loop · DONE] $ARGUMENTS shipped · scratch cleaned. Reminder: green != understood — read what merged.`
