---
description: "Start the gated build loop: plan, grill the plan with you, then plan-review, then halt. Invoke as /anderson:start."
argument-hint: <task-slug> <one-line goal>
allowed-tools: Bash(grep:*), Bash(echo:*)
---
Parse "$ARGUMENTS": FIRST strip an optional `--fable` token from anywhere in it (it is a flag,
not content). THEN task slug = first word of what remains; goal = the rest.

REVIEW MODEL: the plan-reviewer critique gate (PLAN_REVIEW) runs on the model in state.md
`review_model:` — `opus` by default, `fable` when `--fable` was passed. Fable is the stronger
critical analyst; Opus stays the default for the planner (generative), which `--fable` never
touches. Effort stays xhigh either way. The field persists in state.md, so the diff-review gate
in `/anderson:approve-plan` and `/anderson:rework` reads the same choice for this pipeline.

BANNER RULE (every stage): finish ALL stage setup + state.md edits FIRST, then print
the stage banner as the LAST line before the stage's work — immediately above the
agent invocation (for GRILL: above your first question). Per stage: (1) setup,
(2) banner, (3) work — NOTHING between (2) and (3). Never skip a banner; never two
banners back-to-back; never any line between a banner and the agent line.

QUOTE RULE (every banner): pick by COUNTING, never by feel. N = character count of
the task slug (every char, hyphens included); iteration = `iteration:` value read
fresh from state.md (at that point it already reflects this command's increment).
Quote = the 0-based item at index (N + offset + iteration) mod M — offset is given
per banner; M = the integer in that pool's "Pool (M):" label (the label number must
always equal the actual item count; count the list from 0; mod M always yields a
valid 0..M−1). Never "at random"; never default to the first.

SEQUENCING RULE: stages are STRICTLY SEQUENTIAL; each consumes the previous one's
output — the GRILL hardens the plan.md the planner wrote; the plan-reviewer reads
that grilled plan.md. Invoke exactly ONE subagent per message, as the LAST thing in
it, then STOP until it fully finishes. NEVER two stage agents in one message/tool
block — that runs them in PARALLEL: the plan-reviewer judges a plan not yet written
or grilled, and the human grill gets skipped. Planner (step 3) finishes → grill
(step 4, your own interactive step — not a subagent) completes → only then the
plan-reviewer (step 5).

1. Make sure the scratch dir is ignored by git (it's disposable):
   if `feature-research/` is not already in `.gitignore`, append it.
2. If `feature-research/<task>/state.md` is absent, create it with this EXACT block
   (substitute `<task>` with the task slug; set `review_model:` to `fable` if `--fable` was
   parsed from $ARGUMENTS, else leave `opus`). This block is machine-read by
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
   review_model:    opus
   plan_verdict:    pending
   diff_verdict:    pending
   open_questions:  0
   <!-- STATE:END -->

   ## Done so far

   ## Still open

   ## ❓ Open questions
   ```
3. (BANNER + QUOTE RULES, offset +1) Print this PLAN banner as the LAST line before
   invoking the planner, so it sits right above the agent:
   ```
     ╭─ ⌐■-■  PLAN · 1/5 · THE ARCHITECT · opus/high
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (24): "Design twice, so reality only has to happen once." / "The most dangerous flaw is the one the blueprint calls a feature." / "What you do not name in the plan will name itself in production." / "Scope is a fire: contain it or feed it." / "A plan is a promise you make to your future self at 3 a.m." / "Every line you don't write is a line you never debug." / "Decide the hard things on paper, where erasing is cheap." / "The shape of the solution hides in the shape of the problem." / "Cut the scope until it bleeds, then ship the part that lived." / "A blueprint nobody questions is a blueprint nobody read." / "Denial is the most predictable of all human responses." / "Hope: your greatest strength and your greatest weakness." / "As you adequately put, the problem is choice." / "Your life is the sum of a remainder of an unbalanced equation." / "Ergo: vis-à-vis, concordantly." / "There are levels of survival we are prepared to accept." / "I can only show you the door; you are the one who has to walk through it." / "You have to let it all go — fear, doubt, and disbelief." / "You take the red pill, and I show you how deep the rabbit hole goes." / "What you know you can't explain, but you feel it." / "The blueprint is cheaper than the rebuild." / "Name the blast radius before it names you." / "A plan survives contact only if it expected the contact." / "Erase on paper; never in production."
   Then immediately invoke the **planner** subagent (goal = rest of $ARGUMENTS) → writes plan.md. Set stage=grill.
4. (BANNER + QUOTE RULES, offset +2) Print this GRILL banner as the LAST line before
   your FIRST grilling question:
   ```
     ╭─ ⌐■-■  GRILL · 2/5 · THE INTERROGATOR · you
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (24): "Every unanswered question is a bug with a delay." / "The plan you cannot defend out loud is not yet a plan." / "Decide it now in words, or discover it later in an outage." / "An assumption spoken is an assumption you can kill." / "The question you are avoiding is the one that matters." / "Pin every fork before the code picks one for you." / "Vague is just expensive spelled slowly." / "If two answers both sound fine, you haven't found the real question." / "Name the trade-off, or the trade-off names you." / "Shared understanding is cheaper than shared blame." / "What is real? How do you define real?" / "You think that's air you're breathing now?" / "What good is a phone call if you are unable to speak?" / "You have a problem with authority, Mr. Anderson." / "Choice is an illusion created between those with power and those without." / "There is only one constant, one universal: causality." / "Why, Mr. Anderson? Why do you persist?" / "You've been living in a dream world, Neo." / "We are all here to do what we are all here to do." / "Do you believe you are fighting for more than your survival?" / "Every fork you skip, the code picks for you." / "The answer you dodge becomes the outage you explain." / "Defend it out loud, or it isn't decided." / "Do not just hear the plan; interrogate it."
   Then GRILL the plan yourself, inline in this session (self-contained — no external skill):
   - TRIAGE FIRST (before question 1): enumerate every question in ONE pass, drawn ONLY from
     what plan.md already puts on the table — each open branch of its decision tree, every
     `needs-context` row of the "🧯 Error handling" table, and every gap or unjustified entry in
     the "💥 Blast radius" table. The planner already mapped blast radius at plan time; do NOT
     re-sweep the codebase for blindspots here — challenge that table's completeness directly
     (see the blast-radius walk below), and grep a specific caller/test/config ONLY when you
     actually doubt a row. Any question the plan already answers, answer yourself and drop —
     never ask me what the code or the plan already says.
   - Grade every remaining question:
       🔴 ARCH — the answer changes the architecture, data model, or scope
       🟡 BEHAVIOR — edge cases, error handling, UX semantics
       🟢 PREF — naming, defaults, cosmetics; safe to auto-resolve with your recommendation
   - Print the manifest as the FIRST thing after the GRILL banner — ONE header line + a rule,
     nothing else, so I see the grilling level at a glance (substitute real counts; omit a
     grade from the tally when its count is 0):
     ```
     grill · <N> questions · <a>🔴  <b>🟡  <c>🟢
     ──────────────────────────
     ```
   - ASSUME I KNOW THE TOUCHED CODE: keep questions terse, no per-question context or
     explanation sentences, auto-resolve borderline 🟢 to your recommendation. NEVER ask how
     familiar I am with the code — no calibration/meta question of any kind, ever.
   - Order strictly 🔴 → 🟡 → 🟢 (early answers constrain later ones). 🔴 ONE at a time
     (answers cascade); independent 🟡 may pair 2–3 per message when no answer affects
     another; 🟢 one batch. Wait for my answer before the next message. EACH question
     carries your recommended answer so I can just confirm; never restate plan.md content.
   - Print each question in EXACTLY this shape — three lines, the grade dot (🔴/🟡/🟢) the ONLY
     emoji, the bar 10 cells (▰ filled / ▱ empty) with filled = round((n−1)/N × 10) so it grows
     as answers land (empty at the first question), the recommendation the only follow-on line:
     ```
     🔴 <n>/<N>  ▰▰▱▱▱▱▱▱▱▱
        <one-line question>
        → <your recommended answer>
     ```
     If an answer spawns a new question, grow <N> honestly and slot the new one by grade; do
     NOT reprint the manifest — the only drift signal is a dim trailing note on the next
     header line: `🔴 <n>/<N>  <bar>   +1 from your last answer`.
   - 🟢 batch: present ALL preference questions together in ONE message, each with its
     recommendation; a single "defaults fine" accepts every recommendation at once.
   - After each resolved decision, fold it into plan.md (update the affected section; record
     non-obvious choices under a `## Decisions` heading).
   - Explicitly walk the "💥 Blast radius" table: for each vector, challenge whether the
     enumeration is complete and whether out-of-scope calls are justified. Confirm the
     "📈 Scorecard"; if Risk is high or Confidence is low, decide whether to proceed.
   - Walk the "🧯 Error handling" table: resolve every `needs-context` row with me (the handling
     is a business call the plan can't make alone) — give your recommended answer, then on my
     confirmation re-class the row to `deduced` and fold the decision into "✅ Decisions". A row
     left `needs-context` after the grill is a question the human chose to defer, not an oversight.
   - Record the outcome under state.md `## ❓ Open questions`, one line each (same convention auto
     uses, so `/anderson:approve-diff` can lift it into the PR): `[answered] <question> → <answer>
     (grilled)` for each row we resolved together, and `[open] <question> — <why it needs a business
     call>` for each row I chose to DEFER (left `needs-context`). Set `open_questions:` in state.md
     to the count of `[open]` lines. A non-zero count is surfaced in the ship PR, not silently dropped.
   - Continue until I signal shared understanding ("done", "good", "go to review") or no open
     branches remain. On early exit: auto-resolve any unasked 🟢 to your recommendations
     (record each as `[answered] … → … (grilled, default)`), and record any unasked 🔴/🟡 as
     `[open]` — an early exit skips questions, it never silently decides the big ones.
     Then set stage=plan_review and continue to the reviewer.
5. (BANNER + QUOTE RULES, offset +3) Print this PLAN-REVIEW banner as the LAST line
   before invoking the plan-reviewer (substitute `<review_model>` with the state.md value):
   ```
     ╭─ ⌐■-■  PLAN_REVIEW · 3/5 · THE ORACLE · <review_model>/xhigh
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (24): "The flaw hides in the part everyone agreed not to question." / "A question carries more weight than any answer it returns." / "The map is not the territory, and the demo is not the system." / "Ask what it costs before you ask what it does." / "The second pair of eyes sees the assumption the first pair made." / "Improve the plan, not the planner's feelings." / "A good review changes the plan; a great one changes the question." / "Disagree on paper now, or apologize in the incident channel later." / "The cheapest place to be wrong is before the first commit." / "Trust the plan less than the reasons behind it." / "You've already made the choice; now you have to understand it." / "What's really going to bake your noodle is, would you still have broken it if I hadn't said anything?" / "We can never see past the choices we don't understand." / "You have a good soul — and I'm tough on souls." / "I hate giving good people bad news." / "Being the One is like being in love: no one can tell you, you just know it." / "I'd ask you to sit down, but you're not going to anyway." / "Candy?" / "You have the gift, but it looks like you're waiting for something." / "I only ever tell you what you need to hear." / "The assumption nobody stated is the one that breaks." / "Improve the plan, not the planner's mood." / "A second pair of eyes is the cheapest insurance you'll buy." / "I can't make the choice for you; I can make you see it."
   Then immediately invoke the **plan-reviewer** subagent (model override = state.md
   `review_model`, effort xhigh) → makes inline strike-through edits and appends its review
   under `## 🔭 Review` in plan.md; sets plan_verdict.
6. Print and STOP — fill in the real task slug for every `<task>` and the real
   verdict for `<plan_verdict>` so the command + path are copy-pasteable (e.g.
   `/anderson:approve-plan brief-views`, NOT a literal `<task>`):
   ```
   ﾊﾐﾐ 0ｺ1  🔴 G A T E  1 · YOUR TURN  1ｺ0 ﾐﾐﾊ
     ⌐■-■  Read feature-research/<task>/plan.md (## 🔭 Review, verdict=<plan_verdict>), then
            /anderson:approve-plan <task> — or just say "approved, go". Don't implement yet.
   ```
   Halt is unconditional even on a ship verdict.
