---
description: "Start the gated build loop: plan, grill the plan with you, then plan-review, then halt. Invoke as /anderson:start."
argument-hint: <task-slug> <one-line goal>
allowed-tools: Bash(grep:*), Bash(echo:*)
---
Task slug = first word of "$ARGUMENTS"; goal = the rest.

Print this PLAN banner (pick ONE quote at random from the pool — never default to the first, and don't reuse one you showed earlier this session), then act:
```
  ╭─ ⌐■-■  PLAN · 1/4 · THE ARCHITECT · opus/high
  │  "[one quote from the pool]"
  ╰─
```
Pool (10): "Design twice, so reality only has to happen once." / "The most dangerous flaw is the one the blueprint calls a feature." / "What you do not name in the plan will name itself in production." / "Scope is a fire: contain it or feed it." / "A plan is a promise you make to your future self at 3 a.m." / "Every line you don't write is a line you never debug." / "Decide the hard things on paper, where erasing is cheap." / "The shape of the solution hides in the shape of the problem." / "Cut the scope until it bleeds, then ship the part that lived." / "A blueprint nobody questions is a blueprint nobody read."

1. Make sure the scratch dir is ignored by git (it's disposable):
   if `feature-research/` is not already in `.gitignore`, append it.
2. If `feature-research/<task>/state.md` is absent, create it with this EXACT block
   (substitute `<task>` with the task slug). This block is machine-read by
   `hooks/scheduler.py`, `commands/status.md`, and `bin/feature.sh`; the format
   must be byte-faithful — column-0 `key:`, the two STATE comments, no markdown
   bullets or bold:
   ```
   # Pipeline state
   <!-- STATE:START -->
   task:            <task>
   stage:           plan
   gate:            none
   iteration:       0
   max_iterations:  2
   exit_rule:       all tests pass and lint clean, only major issues fixed
   plan_verdict:    pending
   diff_verdict:    pending
   <!-- STATE:END -->

   ## Done so far

   ## Still open
   ```
3. Invoke the **planner** subagent (goal = rest of $ARGUMENTS) → writes plan.md.
   Set stage=grill.
4. Print this GRILL banner (pick ONE quote at random — never default to the first, and don't reuse one you showed earlier this session):
   ```
     ╭─ ⌐■-■  GRILL · harden the plan · THE INTERROGATOR · you
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (10): "Every unanswered question is a bug with a delay." / "The plan you cannot defend out loud is not yet a plan." / "Decide it now in words, or discover it later in an outage." / "An assumption spoken is an assumption you can kill." / "The question you are avoiding is the one that matters." / "Pin every fork before the code picks one for you." / "Vague is just expensive spelled slowly." / "If two answers both sound fine, you haven't found the real question." / "Name the trade-off, or the trade-off names you." / "Shared understanding is cheaper than shared blame."
   Then GRILL the plan yourself, inline in this session (self-contained — no external skill):
   - Ask ONE question at a time; wait for my answer before the next.
   - Walk down each branch of plan.md's decision tree, resolving dependencies between
     decisions one-by-one. For EACH question give your recommended answer, so I can just confirm.
   - If a question can be answered by exploring the codebase, explore instead of asking.
   - After each resolved decision, fold it into plan.md (update the affected section; record
     non-obvious choices under a `## Decisions` heading).
   - Continue until I signal shared understanding ("done", "good", "go to review") or no open
     branches remain. Then set stage=plan_review and continue to the reviewer.
5. Print this PLAN-REVIEW banner (pick ONE quote at random — never default to the first, and don't reuse one you showed earlier this session):
   ```
     ╭─ ⌐■-■  PLAN_REVIEW · 2/4 · THE ORACLE · opus/xhigh
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (10): "The flaw hides in the part everyone agreed not to question." / "A question carries more weight than any answer it returns." / "The map is not the territory, and the demo is not the system." / "Ask what it costs before you ask what it does." / "The second pair of eyes sees the assumption the first pair made." / "Improve the plan, not the planner's feelings." / "A good review changes the plan; a great one changes the question." / "Disagree on paper now, or apologize in the incident channel later." / "The cheapest place to be wrong is before the first commit." / "Trust the plan less than the reasons behind it."
   Invoke the **plan-reviewer** subagent → edits plan.md in place, prepends
   "## Diverged because", keeps plan.orig.md, sets plan_verdict.
6. Print and STOP — fill in the real task slug for every `<task>` and the real
   verdict for `<plan_verdict>` so the command + path are copy-pasteable (e.g.
   `/anderson:approve-plan brief-views`, NOT a literal `<task>`):
   `■ GATE 1 · your turn. Read feature-research/<task>/plan.md (## Diverged because, verdict=<plan_verdict>). Then /anderson:approve-plan <task> — or just say "approved, go". Don't implement yet.`
   Halt is unconditional even on a ship verdict.
