---
description: "Start the gated build loop: plan, grill the plan with you, then plan-review, then halt. Invoke as /anderson:start."
argument-hint: <task-slug> <one-line goal>
allowed-tools: Bash(grep:*), Bash(echo:*), Bash(sed:*)
---
State first, so the fleet monitor shows this task's row before any thinking starts (idempotent;
also adds `feature-research/` to .gitignore):
!`bash "${CLAUDE_PLUGIN_ROOT}/bin/feature.sh" seed $1 $2 2>&1`

Parse "$ARGUMENTS": FIRST strip an optional `--opus` token from anywhere in it (it is a flag,
not content). THEN task slug = first word of what remains; goal = the rest.

SLUG WITH A SLASH: people paste branch names as the slug (Linear style:
`amcleanjanet/ar-2587-backoffice-ui-polish`). The task key is the LAST `/`-segment
(`ar-2587-backoffice-ui-polish`) so `feature-research/<task>/` stays flat (nested dirs are
invisible to the statusline, the scheduler and the fleet monitor). When the slug had a `/`,
add `branch:          <slug as given>` to the STATE block right after `task:` — ship uses it
verbatim as the branch name instead of `anderson/<task>`. Refer to the task by its key everywhere
below; `<task>` means the key.

REVIEW MODEL: the plan-reviewer critique gate (PLAN_REVIEW) runs on the model in state.md
`review_model:` — `fable` by default, `opus` when `--opus` was passed. Fable is the stronger
critical analyst AND the cheaper one per unit of quality (it scores higher than Opus at every
effort level while using fewer tokens), so `--opus` is an escape valve for when the Fable budget
is exhausted, not a quality upgrade. Opus stays the default for the planner (generative), which
`--opus` never touches. The field persists in state.md, so the diff-review gate in
`/anderson:approve-plan` and `/anderson:rework` reads the same choice for this pipeline.

TIER: difficulty routing, so a one-line fix does not pay for a two-xhigh-critique pipeline.
Computed ONCE at step 5 from the planner's `## 📈 Scorecard` (it does not exist before the
planner runs, which is why the seed leaves `tier: pending`). First match wins, top-down:
  - CRITICAL — Risk ≥ 9 OR Testability ≥ 7 (the scorecard anchor "needs a human/manual tester").
  - HARD     — Risk ≥ 7 OR Coupling ≥ 7 OR Confidence ≤ 4, OR the change touches security, auth,
               memory/resource management, concurrency, or OS/filesystem/process boundaries.
  - TRIVIAL  — Risk ≤ 2 AND Coupling ≤ 3 AND Confidence ≥ 8 (all three, or it is not trivial).
  - NORMAL   — anything else (default).
Record `tier: <trivial|normal|hard|critical>` in state.md. PROVISIONAL — `/anderson:approve-plan`
re-tiers against the actual diff and takes the MAX (tier only ever escalates, never drops).

REVIEW EFFORT: derived from `tier`, never from the flag. The plan critique runs ONE rung ABOVE
the diff critique (capped at xhigh), because plan.md is the reference every downstream check
validates against — the implementer executes it verbatim and the diff reviewer checks the diff
AGAINST it, so a wrong plan is invisible to everything after it, while a missed diff bug still
faces CI, the implementer's tests, and your Gate 2 read.
  | tier     | PLAN_REVIEW | DIFF_REVIEW |
  | trivial  | skipped     | medium      |
  | normal   | high        | medium      |
  | hard     | xhigh       | high        |
  | critical | xhigh       | xhigh       |
Never `max` (buys +0.6 points for +20k tokens) and never `low` (quality falls off a cliff below
medium). The usable band is medium → xhigh.

BANNER RULE: finish setup and state.md edits, then print the banner as the last line before
the agent call.

QUOTE: pick one line from the stage's pool; vary it across stages.

SEQUENCING: stages are sequential because each reads the previous stage's file output
(the reviewer reads the diff + audit.md the implementer just wrote). Invoke one subagent
per message, as its last line, and wait for it to finish — two Agent calls in one message
run in parallel and the reviewer judges files that don't exist yet.

1. The seed line at the top already did the setup: `.gitignore` has `feature-research/` and
   `feature-research/<task>/state.md` exists (`state: … seeded` or `… already there`). Do NOT
   recreate it. Only when that line reports an error or is missing, do steps 1-2 by hand:
   append `feature-research/` to `.gitignore` if absent, and create state.md as in step 2.
   If `--opus` was parsed but the seed line says `review_model fable` (the flag sat past the
   second word), fix it: `sed -i.bak -E 's/^(review_model:[[:space:]]*).*/\1opus/' feature-research/<task>/state.md && rm -f feature-research/<task>/state.md.bak`.
2. FALLBACK ONLY — if `feature-research/<task>/state.md` is absent, create it with this EXACT block
   (substitute `<task>` with the task slug; set `review_model:` to `opus` if `--opus` was
   parsed from $ARGUMENTS, else leave `fable`). This block is machine-read by
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
   review_model:    fable
   tier:            pending
   source_url:      none
   plan_verdict:    pending
   diff_verdict:    pending
   open_questions:  0
   <!-- STATE:END -->

   ## Done so far

   ## Still open

   ## ❓ Open questions
   ```
2b. INTAKE — normalize ticket + design into scratch BEFORE the planner (skip silently when
   the goal references neither):
   - TICKET: goal contains a ticket URL/id (Linear, GitHub, Jira …) → fetch it (MCP or `gh`);
     set state.md `source_url:` to the URL; hand any acceptance-criteria section to the
     planner VERBATIM (`source: ticket`). Unreachable → note it, continue.
   - DESIGN: goal or ticket references a design (figma.com URL, image path, image attached to
     the ticket) → normalize into `feature-research/<task>/design/`:
     Figma URL → MCP `get_screenshot` (+ `get_design_context` for exact strings) ·
     ticket attachment → download it (e.g. Linear MCP `extract_images`) ·
     local image path → copy it ·
     no tool reaches it → ask me to drop the file into `design/`, wait, continue.
     Then write `design/inventory.md`: every EXACT text string (quoted character-faithful),
     every state/variant shown, layout facts (order, grouping, alignment). The planner turns
     inventory lines into `source: design` criteria; the diff reviewer compares the built UI
     against these files.
   Pass to the planner: goal + ticket criteria (verbatim) + the `design/` path when present.

3. Print this PLAN banner as the LAST line before
   invoking the planner, so it sits right above the agent:
   ```
     ╭─ ⌐■-■  PLAN · 1/5 · THE ARCHITECT · opus/high
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (24): "Design twice, so reality only has to happen once." / "The most dangerous flaw is the one the blueprint calls a feature." / "What you do not name in the plan will name itself in production." / "Scope is a fire: contain it or feed it." / "A plan is a promise you make to your future self at 3 a.m." / "Every line you don't write is a line you never debug." / "Decide the hard things on paper, where erasing is cheap." / "The shape of the solution hides in the shape of the problem." / "Cut the scope until it bleeds, then ship the part that lived." / "A blueprint nobody questions is a blueprint nobody read." / "Denial is the most predictable of all human responses." / "Hope: your greatest strength and your greatest weakness." / "As you adequately put, the problem is choice." / "Your life is the sum of a remainder of an unbalanced equation." / "Ergo: vis-à-vis, concordantly." / "There are levels of survival we are prepared to accept." / "I can only show you the door; you are the one who has to walk through it." / "You have to let it all go — fear, doubt, and disbelief." / "You take the red pill, and I show you how deep the rabbit hole goes." / "What you know you can't explain, but you feel it." / "The blueprint is cheaper than the rebuild." / "Name the blast radius before it names you." / "A plan survives contact only if it expected the contact." / "Erase on paper; never in production."
   Then immediately invoke the **planner** subagent (goal = rest of $ARGUMENTS) → writes plan.md. Set stage=grill.
4. Print this GRILL banner as the LAST line before
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
     `derived` row of the "✅ Acceptance criteria" table, every `needs-context` row of the
     "🧯 Error handling" table, and every gap or unjustified entry in the "💥 Blast radius" table. The planner already mapped blast radius at plan time; do NOT
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
   - Walk the "✅ Acceptance criteria" table: every `derived` row is a 🔴 question (confirm /
     edit / drop — a wrong criterion poisons every downstream check); `ticket`/`design` rows
     are batch-confirmed in one line unless you doubt one. A criterion I add gets
     `source: ticket` (I am the ticket).
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
   - LB ASSUMPTIONS ARE NON-DEFERRABLE. Every `## ✅ Decisions` row classed **LB** is always a 🔴
     and MUST be answered by me before you leave the grill — it cannot be auto-resolved, batched,
     or left `[open]`. On my confirmation, flip its `Confirmed` cell ✗ → ✓ and record `[answered]
     … → … (grilled)`. If I edit the guess, fold the new value in. An LB row still ✗ = the maker
     guessed the target and I never ratified it: the single most expensive way to ship the wrong
     thing, so the gate refuses to advance while any remains (below).
   - Continue until I signal shared understanding ("done", "good", "go to review") or no open
     branches remain. On early exit: auto-resolve any unasked 🟢 to your recommendations
     (record each as `[answered] … → … (grilled, default)`), and record any unasked 🟡 (and any
     🔴 that is NOT an LB row) as `[open]` — an early exit skips questions, it never silently
     decides the big ones, and it can NEVER skip an LB row. If any LB row is still ✗, do not exit:
     print the unconfirmed LB rows and ask me to resolve them. Only once every LB row is ✓ set
     stage=plan_review and continue to the reviewer.
5. ROUTE — read the `## 📈 Scorecard` Planner column from plan.md (Risk, Coupling, Confidence,
   Testability) and compute the tier per TIER above. Write `tier: <t>` to state.md. Then read the
   PLAN_REVIEW row of the REVIEW EFFORT table for `<review_effort>`.

   TRIVIAL SHORTCUT: if `tier: trivial`, SKIP the plan-reviewer entirely — a trivial plan you have
   already grilled does not earn a critique. Set `plan_verdict: skipped-trivial`, print
   `■ PLAN_REVIEW · skipped (tier trivial)`, and go straight to step 6. The gate still halts:
   you read the plan at Gate 1 either way, and that card is the check.

   Otherwise print this PLAN-REVIEW banner as the LAST line before invoking the plan-reviewer
   (substitute `<review_model>` and `<review_effort>` with the state.md / table values):
   ```
     ╭─ ⌐■-■  PLAN_REVIEW · 3/5 · THE ORACLE · <review_model>/<review_effort>
     │  "[one quote from the pool]"
     ╰─
   ```
   Pool (24): "The flaw hides in the part everyone agreed not to question." / "A question carries more weight than any answer it returns." / "The map is not the territory, and the demo is not the system." / "Ask what it costs before you ask what it does." / "The second pair of eyes sees the assumption the first pair made." / "Improve the plan, not the planner's feelings." / "A good review changes the plan; a great one changes the question." / "Disagree on paper now, or apologize in the incident channel later." / "The cheapest place to be wrong is before the first commit." / "Trust the plan less than the reasons behind it." / "You've already made the choice; now you have to understand it." / "What's really going to bake your noodle is, would you still have broken it if I hadn't said anything?" / "We can never see past the choices we don't understand." / "You have a good soul — and I'm tough on souls." / "I hate giving good people bad news." / "Being the One is like being in love: no one can tell you, you just know it." / "I'd ask you to sit down, but you're not going to anyway." / "Candy?" / "You have the gift, but it looks like you're waiting for something." / "I only ever tell you what you need to hear." / "The assumption nobody stated is the one that breaks." / "Improve the plan, not the planner's mood." / "A second pair of eyes is the cheapest insurance you'll buy." / "I can't make the choice for you; I can make you see it."
   Then immediately invoke the **plan-reviewer** subagent (model override = state.md
   `review_model`, effort = `<review_effort>` per REVIEW EFFORT) → makes inline strike-through
   edits and appends its review under `## 🔭 Review` in plan.md; sets plan_verdict.
6. Print the GATE 1 TL;DR card and STOP. Fill EVERY value from plan.md/state.md (real slug,
   real verdict, real counts — copy-pasteable, no literal `<task>`); omit zero-count entries
   from the criteria line. The card is the TL;DR — open plan.md only when a line raises doubt:
   ```
   ﾊﾐﾐ 0ｺ1  🔴 G A T E  1 · YOUR TURN  1ｺ0 ﾐﾐﾊ
     ⌐■-■  <plan.md ## 🎯 What, first line>
           criteria <N> (<t> ticket · <d> design · <x> derived · <n> contract) · proof: <a> test · <b> visual · <c> e2e · <p> contract · <m> manual
           assumptions: <n> load-bearing · all confirmed ✓   (each criterion has its own proof)
           scorecard: Risk <r> · Confidence <c> · Coupling <k> · Reversibility <v>
           verdict <plan_verdict> → /anderson:approve-plan <task> — or "approved, go" · full plan: feature-research/<task>/plan.md
   ```
   Halt is unconditional even on a ship verdict. GATE-BLOCK RULE: the gate is not approvable while
   any `## ✅ Decisions` LB row is unconfirmed (✗) — the grill above should have caught this, but
   if any remains, replace the "YOUR TURN" card with a `🔴 GATE 1 BLOCKED — <n> load-bearing
   assumptions unconfirmed` card listing each, and resolve them with me before offering approval.
