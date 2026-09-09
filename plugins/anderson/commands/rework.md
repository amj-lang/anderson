---
description: "Loop the implementer on the checker's blocking findings, then diff-review and halt."
argument-hint: <task-slug>
---
Task slug = "$ARGUMENTS"; the task key (state dir name) is its LAST `/`-segment, so a pasted
branch name like `user/ar-123-title` resolves to `feature-research/ar-123-title/`.
Blocking findings are already in state.md "Still open".
Run exactly the implement → diff_review → halt sequence from approve-plan,
incrementing iteration and stopping if it exceeds max_iterations.

REVIEW MODEL: the diff-review gate runs on the model in state.md `review_model:` (`fable` default,
`opus` if the pipeline was started with `--opus`; missing field → treat as `fable`). Read it
fresh; the implementer is unaffected.

REVIEW EFFORT: derived from state.md `tier`, never from a flag.
RE-TIER FIRST — before reading the effort, re-tier against the ACTUAL diff and take the MAX (tier
only ever escalates, never drops). `git diff --stat` showing ≥150 lines OR ≥8 files → at least
HARD; a diff touching security, auth, memory/resource management, concurrency, or
OS/filesystem/process boundaries → at least HARD. Write the resulting `tier:` back to state.md.
Then read the effort off it:
  | tier     | DIFF_REVIEW effort |
  | trivial  | medium             |
  | normal   | medium             |
  | hard     | high               |
  | critical | xhigh              |
Missing or `pending` tier (a pipeline started before tiering existed) → treat as `hard`. Never
`max`, never `low`. Pass the resolved value as the per-invocation effort override and print it as
`<review_effort>` in the banner.

BANNER RULE: finish setup and state.md edits, then print the banner as the last line before
the agent call. Both stages get one — IMPLEMENT before the implementer, DIFF_REVIEW before
the reviewer.

SEQUENCING: stages are sequential because each reads the previous stage's file output
(the reviewer reads the diff + audit.md the implementer just wrote). Invoke one subagent
per message, as its last line, and wait for it to finish — two Agent calls in one message
run in parallel and the reviewer judges files that don't exist yet.

1. In state.md set iteration += 1 (if iteration > max_iterations, print `■ EXIT · hit max_iterations` and STOP); set stage=implement, then (BANNER RULE) print this IMPLEMENT banner as the LAST line before invoking the implementer:
   ```
     ╭─ ⌐■-■  IMPLEMENT · 4/5 · NEO · sonnet/medium
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool: same as approve-plan.md step 1.
   Then invoke the implementer subagent: fix only "Still open". Writes audit.md.
   Set stage=diff_review.
2. (BANNER RULE) Print this DIFF-REVIEW banner as the LAST line before invoking the reviewer (substitute `<review_model>` with the state.md value):
   ```
     ╭─ ⌐■-■  DIFF_REVIEW · 5/5 · AGENT SMITH · <review_model>/<review_effort>
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool: same as approve-plan.md step 2.
   Then invoke the reviewer subagent (model override = state.md `review_model`, effort = `<review_effort>` per REVIEW EFFORT) → appends diff review under `## 🔭 Review` in plan.md; sets diff_verdict.
3. Print the GATE 2 line exactly as approve-plan.md step 3 does, then STOP.
