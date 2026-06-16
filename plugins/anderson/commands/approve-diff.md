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
3. Print this SHIP banner (pick ONE ending at random from the 10 — never default to the first, and don't reuse one you showed earlier this session), then the done line:
   ```
     ✦ ⌐■-■  A N D E R S O N  ✦   ·   ✓ · SHIP
           THE ONE · welcome to the real world
           "[one quote from the pool]"
   ```
   Pool (10 endings): "Green is not understood; read what you merged." / "The gate is not an obstacle; it is the point." / "Review is how respect for the future is spelled." / "You can hand someone the key, but the lock is theirs to turn." / "Ship it, then watch it — shipping is the start of knowing." / "The work is done when the next person needs no story to follow it." / "Every merge is a promise the next outage will test." / "Walk away clean: no scratch, no secrets, no surprises." / "What you shipped is now the truth; make sure it tells no lies." / "The loop ends where your judgement begins."
   Then: `✓ [anderson · DONE] $ARGUMENTS shipped · scratch cleaned · loop stopped — nothing runs in the background; /anderson:start to begin again. Reminder: green != understood — read what merged.`
