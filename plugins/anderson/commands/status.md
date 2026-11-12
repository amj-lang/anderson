---
description: "Show the loop dashboard for a task and the subagent model override."
argument-hint: <task-slug>
allowed-tools: Bash(echo:*), Bash(cat:*), Bash(basename:*)
effort: low
---
Subagent model env (a default only: agent frontmatter wins unless `_FORCE=1` is also set):
!`echo "CLAUDE_CODE_SUBAGENT_MODEL=${CLAUDE_CODE_SUBAGENT_MODEL:-<unset>} CLAUDE_CODE_SUBAGENT_MODEL_FORCE=${CLAUDE_CODE_SUBAGENT_MODEL_FORCE:-<unset>}"`

State for "$ARGUMENTS" (task key = last `/`-segment, so a pasted branch name resolves to the flat dir):
!`cat "feature-research/$(basename "$ARGUMENTS")/state.md" 2>/dev/null | sed -n '/STATE:START/,/STATE:END/p'`

Summarize for me: current stage, which agent runs next and at what model/effort, both verdicts,
`tier`, and iteration vs max_iterations. The review seats are derived from state.md `tier`:
  | tier     | PLAN_REVIEW | DIFF_REVIEW                  |
  | trivial  | opus/medium | none (you review the diff)   |
  | normal   | opus/high   | opus/high                    |
  | hard     | opus/high   | fable/high                   |
  | critical | fable/high  | fable/high                   |
A missing or `pending` tier means the tier has not been computed yet (it is derived from the
plan Scorecard right after the planner returns) or the run predates tiering — report it as `normal`.
An older state.md may still carry a `review_model:` field — ignore it.
If `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` is set with `CLAUDE_CODE_SUBAGENT_MODEL`, report that
model as the override in effect over every stage's declared model, not as an error to clear;
without `_FORCE` the frontmatter models above run. One short block, no padding. If stage is
`grill`, the next step is the interactive grilling of the plan (no subagent, no model)
before plan-review. If `plan_verdict` is `regrill`, the loop has been routed back to the
grill step (human-gated) for another interview pass; report that the next step is grilling,
not plan-review.
When reading field values, parse leniently: strip any leading `- ` bullet or
leading/trailing `**` bold markers, and ignore any trailing `# comment`. The
machine-canonical format is `key:  value` at column 0, but markdown-styled
state files (with bullets or bold) must render the same field values.
