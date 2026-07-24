---
description: "Show the loop dashboard for a task and the subagent model override."
argument-hint: <task-slug>
allowed-tools: Bash(echo:*), Bash(cat:*)
---
Subagent model override (in effect over agent frontmatter when set):
!`echo "CLAUDE_CODE_SUBAGENT_MODEL=${CLAUDE_CODE_SUBAGENT_MODEL:-<unset>}"`

State for "$ARGUMENTS":
!`cat "feature-research/$ARGUMENTS/state.md" 2>/dev/null | sed -n '/STATE:START/,/STATE:END/p'`

Summarize for me: current stage, which agent runs next and at what model/effort,
both verdicts, and iteration vs max_iterations. For the review stages (plan-review,
diff-review) the model is state.md `review_model` (`opus` default, `fable` when the
pipeline was started with `--fable`); a missing field means an older run — treat as `opus`.
If `CLAUDE_CODE_SUBAGENT_MODEL` is set, report it as the override in effect over the
stage's declared model, not as an error to clear. One short block, no padding. If stage is
`grill`, the next step is the interactive grilling of the plan (no subagent, no model)
before plan-review. If `plan_verdict` is `regrill`, the loop has been routed back to the
grill step (human-gated) for another interview pass; report that the next step is grilling,
not plan-review.
When reading field values, parse leniently: strip any leading `- ` bullet or
leading/trailing `**` bold markers, and ignore any trailing `# comment`. The
machine-canonical format is `key:  value` at column 0, but markdown-styled
state files (with bullets or bold) must render the same field values.
