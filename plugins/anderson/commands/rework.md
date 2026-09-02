---
description: "Loop the implementer on the checker's blocking findings, then diff-review and halt."
argument-hint: <task-slug>
---
Task slug = "$ARGUMENTS". Blocking findings are already in state.md "Still open".
Run exactly the implement → diff_review → halt sequence from approve-plan,
incrementing iteration and stopping if it exceeds max_iterations.

REVIEW MODEL: the diff-review gate runs on the model in state.md `review_model:` (`fable` default,
`opus` if the pipeline was started with `--opus`; missing field → treat as `fable`). Read it
fresh; the implementer is unaffected.

REVIEW EFFORT: the reviewer runs at `high` (its frontmatter default). Raise to `xhigh` only when
the plan's `## 📈 Scorecard` shows Risk ≥ 8 or the change touches security, auth, memory/resource
management, concurrency, or OS/filesystem/process boundaries — pass `effort xhigh` as the
per-invocation override and print `<review_effort>` = `xhigh` in the banner; else `high`.

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
