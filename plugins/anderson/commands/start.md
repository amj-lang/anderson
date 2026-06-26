---
description: "Start the gated build loop: plan, grill the plan with you, then plan-review, then halt. Invoke as /anderson:start."
argument-hint: <task-slug> <one-line goal>
allowed-tools: Bash(grep:*), Bash(echo:*)
---
Task slug = first word of "$ARGUMENTS"; goal = the rest.

BANNER RULE (applies to every stage below): finish ALL of a stage's setup
and state.md edits FIRST, then print that stage's banner as the LAST line you
emit before the stage's work begins — i.e. immediately above the agent
invocation (or, for GRILL, immediately above your first question). Per stage,
in order: (1) do the setup, (2) print the banner, (3) start the work — NOTHING
between (2) and (3). Never skip a stage's banner; never print two banners
back-to-back; never let any other line fall between a banner and the agent line.

1. Make sure the scratch dir is ignored by git (it's disposable):
   if `feature-research/` is not already in `.gitignore`, append it.
2. If `feature-research/<task>/state.md` is absent, create it with this EXACT block
   (substitute `<task>` with the task slug). This block is machine-read by
   `hooks/scheduler.py`, `commands/status.md`, and `bin/feature.sh` — byte-faithful:
   column-0 `key:`, the two STATE comments, no markdown bullets or bold:
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
3. (BANNER RULE) Print this PLAN banner (choose the quote by COUNTING, not by feel: let N = the number of characters in the
   task slug (just its length — count every character, including hyphens); let iteration
   = the `iteration:` value currently in state.md (read it fresh — at this step it already
   reflects this command's increment); the quote is the 0-based item at index
   (N + 1 + iteration) mod M, where M is the integer printed in the "Pool (M):" label
   below — count the list from 0; mod M always yields a valid position (0 to M−1).
   (M is read from the label, so the label number must always equal the actual item count.)
   Do NOT pick "at random" and do NOT default to the first.) as the LAST line before invoking
   the planner, so it sits right above the agent:
   ```
     ╭─ ⌐■-■  PLAN · 1/5 · THE ARCHITECT · opus/high
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (24): "Design twice, so reality only has to happen once." / "The most dangerous flaw is the one the blueprint calls a feature." / "What you do not name in the plan will name itself in production." / "Scope is a fire: contain it or feed it." / "A plan is a promise you make to your future self at 3 a.m." / "Every line you don't write is a line you never debug." / "Decide the hard things on paper, where erasing is cheap." / "The shape of the solution hides in the shape of the problem." / "Cut the scope until it bleeds, then ship the part that lived." / "A blueprint nobody questions is a blueprint nobody read." / "Denial is the most predictable of all human responses." / "Hope: your greatest strength and your greatest weakness." / "As you adequately put, the problem is choice." / "Your life is the sum of a remainder of an unbalanced equation." / "Ergo: vis-à-vis, concordantly." / "There are levels of survival we are prepared to accept." / "I can only show you the door; you are the one who has to walk through it." / "You have to let it all go — fear, doubt, and disbelief." / "You take the red pill, and I show you how deep the rabbit hole goes." / "What you know you can't explain, but you feel it." / "The blueprint is cheaper than the rebuild." / "Name the blast radius before it names you." / "A plan survives contact only if it expected the contact." / "Erase on paper; never in production."
   Then immediately invoke the **planner** subagent (goal = rest of $ARGUMENTS) → writes plan.md. Set stage=grill.
4. (BANNER RULE) Print this GRILL banner (choose the quote by COUNTING, not by feel: let N = the number of characters in the
   task slug (just its length — count every character, including hyphens); let iteration
   = the `iteration:` value currently in state.md (read it fresh — at this step it already
   reflects this command's increment); the quote is the 0-based item at index
   (N + 2 + iteration) mod M, where M is the integer printed in the "Pool (M):" label
   below — count the list from 0; mod M always yields a valid position (0 to M−1).
   (M is read from the label, so the label number must always equal the actual item count.)
   Do NOT pick "at random" and do NOT default to the first.) as the LAST line before your FIRST grilling question:
   ```
     ╭─ ⌐■-■  GRILL · 2/5 · THE INTERROGATOR · you
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (24): "Every unanswered question is a bug with a delay." / "The plan you cannot defend out loud is not yet a plan." / "Decide it now in words, or discover it later in an outage." / "An assumption spoken is an assumption you can kill." / "The question you are avoiding is the one that matters." / "Pin every fork before the code picks one for you." / "Vague is just expensive spelled slowly." / "If two answers both sound fine, you haven't found the real question." / "Name the trade-off, or the trade-off names you." / "Shared understanding is cheaper than shared blame." / "What is real? How do you define real?" / "You think that's air you're breathing now?" / "What good is a phone call if you are unable to speak?" / "You have a problem with authority, Mr. Anderson." / "Choice is an illusion created between those with power and those without." / "There is only one constant, one universal: causality." / "Why, Mr. Anderson? Why do you persist?" / "You've been living in a dream world, Neo." / "We are all here to do what we are all here to do." / "Do you believe you are fighting for more than your survival?" / "Every fork you skip, the code picks for you." / "The answer you dodge becomes the outage you explain." / "Defend it out loud, or it isn't decided." / "Do not just hear the plan; interrogate it."
   Then GRILL the plan yourself, inline in this session (self-contained — no external skill):
   - Ask ONE question at a time; wait for my answer before the next.
   - Walk down each branch of plan.md's decision tree, resolving dependencies between
     decisions one-by-one. For EACH question give your recommended answer, so I can just confirm.
   - If a question can be answered by exploring the codebase, explore instead of asking.
   - After each resolved decision, fold it into plan.md (update the affected section; record
     non-obvious choices under a `## Decisions` heading).
   - Explicitly walk the "💥 Blast radius" table: for each vector, challenge whether the
     enumeration is complete and whether out-of-scope calls are justified. Confirm the
     "📈 Scorecard"; if Risk is high or Confidence is low, decide whether to proceed.
   - Walk the "🧯 Error handling" table: resolve every `needs-context` row with me (the handling
     is a business call the plan can't make alone) — give your recommended answer, then on my
     confirmation re-class the row to `deduced` and fold the decision into "✅ Decisions". A row
     left `needs-context` after the grill is a question the human chose to defer, not an oversight.
   - Continue until I signal shared understanding ("done", "good", "go to review") or no open
     branches remain. Then set stage=plan_review and continue to the reviewer.
5. (BANNER RULE) Print this PLAN-REVIEW banner (choose the quote by COUNTING, not by feel: let N = the number of characters in the
   task slug (just its length — count every character, including hyphens); let iteration
   = the `iteration:` value currently in state.md (read it fresh — at this step it already
   reflects this command's increment); the quote is the 0-based item at index
   (N + 3 + iteration) mod M, where M is the integer printed in the "Pool (M):" label
   below — count the list from 0; mod M always yields a valid position (0 to M−1).
   (M is read from the label, so the label number must always equal the actual item count.)
   Do NOT pick "at random" and do NOT default to the first.) as the LAST line before invoking
   the plan-reviewer:
   ```
     ╭─ ⌐■-■  PLAN_REVIEW · 3/5 · THE ORACLE · opus/xhigh
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (24): "The flaw hides in the part everyone agreed not to question." / "A question carries more weight than any answer it returns." / "The map is not the territory, and the demo is not the system." / "Ask what it costs before you ask what it does." / "The second pair of eyes sees the assumption the first pair made." / "Improve the plan, not the planner's feelings." / "A good review changes the plan; a great one changes the question." / "Disagree on paper now, or apologize in the incident channel later." / "The cheapest place to be wrong is before the first commit." / "Trust the plan less than the reasons behind it." / "You've already made the choice; now you have to understand it." / "What's really going to bake your noodle is, would you still have broken it if I hadn't said anything?" / "We can never see past the choices we don't understand." / "You have a good soul — and I'm tough on souls." / "I hate giving good people bad news." / "Being the One is like being in love: no one can tell you, you just know it." / "I'd ask you to sit down, but you're not going to anyway." / "Candy?" / "You have the gift, but it looks like you're waiting for something." / "I only ever tell you what you need to hear." / "The assumption nobody stated is the one that breaks." / "Improve the plan, not the planner's mood." / "A second pair of eyes is the cheapest insurance you'll buy." / "I can't make the choice for you; I can make you see it."
   Then immediately invoke the **plan-reviewer** subagent → makes inline strike-through
   edits and appends its review under `## 🔭 Review` in plan.md; sets plan_verdict.
6. Print and STOP — fill in the real task slug for every `<task>` and the real
   verdict for `<plan_verdict>` so the command + path are copy-pasteable (e.g.
   `/anderson:approve-plan brief-views`, NOT a literal `<task>`):
   ```
   ﾊﾐﾐ 0ｺ1  🔴 G A T E  1 · YOUR TURN  1ｺ0 ﾐﾐﾊ
     ⌐■-■  Read feature-research/<task>/plan.md (## 🔭 Review, verdict=<plan_verdict>), then
            /anderson:approve-plan <task> — or just say "approved, go". Don't implement yet.
   ```
   Halt is unconditional even on a ship verdict.
