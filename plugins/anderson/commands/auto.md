---
description: "Run the full plan → implement → review pipeline non-halting to a draft PR — no human gates. Experimental autonomous mode."
argument-hint: <task-id> <title> [body|@taskspec-file]
allowed-tools: Bash, Read, Edit, Write
---
Parse $ARGUMENTS: FIRST strip an optional `--fable` token from anywhere in $ARGUMENTS
(it is a flag, not content) — if present, the two review gates run on Fable instead of
Opus (see REVIEW MODEL below); record it for the state seed. THEN from the remaining
words: first word = task-id (run-lock key + state dir name); second word = title;
remainder = body (or @path to TaskSpec file on disk). task-id and title required;
body optional (acceptance_criteria derived if absent).

REVIEW MODEL: the two critique gates (PLAN GATE plan-reviewer, DIFF GATE reviewer panel
+ arbiter) run on the model in state.md `review_model:` — `opus` by default, `fable` when
`--fable` was passed. Fable is the stronger critical analyst; Opus stays the default for the
generative stages (planner, implementer), which `--fable` never touches. Effort stays xhigh
either way. Every banner and invocation below reads `review_model` from state.md.

BANNER RULE (every stage below): finish ALL setup and state.md edits for stage FIRST,
then print stage's banner as LAST line before stage's work begins (immediately
above agent invocation or action). Nothing between banner and work. Never
skip banner; never print two banners back-to-back. Unlike gated commands, this command
NEVER prints a GATE line and NEVER halts for a human — self-sequences all 9 steps in one turn.
Terminal states: SHIP (stage: done, draft PR) or abort (stage: aborted with structured report).

AUTO-MODE OVERRIDE POLICY (operator opt-in — GOVERNS steps below; where later step conflicts,
THIS section wins). auto mode runs unattended, expected to FINISH task, not bail to human
for soft guardrails. Own branch + draft PR are its SANDBOX: inside that PR it may create
draft, push to it, update description, squash own commits. Must not reach outside it.

RELAX (do NOT abort or stop run for these — push through, complete task, NOTE
condition under `## Done so far` + in PR body so reviewer sees it):
- Planner confidence ≤ 3 (step 3a) — proceed; record low confidence, add `needs-human` label
  at SHIP instead of aborting.
- Runaway-refactor cap >200 lines / >20 files (step 7d) — proceed; record size; do NOT fail gate.
- scope_paths violations (step 7d) — proceed; note out-of-scope files; do NOT fail gate.
- Sensitive NON-migration paths — `.github/`, CI config, `*.lock`/lockfiles, dependency manifests,
  `.env`, `*.pem`, `*.key` (step 7d) — auto MAY change these when task requires; attach
  `needs-human` label as heads-up but do NOT abort, do NOT fail gate.

KEEP unchanged (verification engine + cost backstops, NOT blockers — stay exactly
as written): baseline-green precondition (step 2); test_cmd resolution incl. needs-spec when
truly un-inferable (verification needs test command); RED + red-for-right-reason (step 5);
test-tamper guard (7b); CI veto (7c); blind panel + arbiter (7f/7g); thrash breaker / replan
bounce / max_iterations budget (7h).

NON-NEGOTIABLE HARD RULES (no override, ever):
1. NEVER author or apply a database migration. If task requires schema/data migration, STOP:
   write NO migration file, write hand-off report (reason `needs-migration`), set `stage: aborted`,
   print it, STOP. The one forbidden path that stays a HARD STOP.
2. NEVER force-push any branch EXCEPT auto's own `anderson/auto/<task-id>-<slug>` branch. Force-push
   (use `--force-with-lease`) allowed ONLY on that own branch — e.g. to squash run's commits
   into one clean commit for tidy release history. Force-pushing default branch, shared
   branch, or human-authored branch requires explicit human consent.

BANNER POOL — auto stages use these Matrix-flavoured banners in framed `╭─ ⌐■-■` format.
In the two review banners (PLAN GATE, DIFF GATE) `<review_model>` is a placeholder: substitute
the state.md `review_model:` value (`opus` or `fable`) when printing.

INGEST banner (stage offset 1):
```
  ╭─ ⌐■-■  INGEST · 1/9 · THE OPERATOR · auto
  │  "[quote from INGEST pool]"
  ╰─
```
INGEST pool (14): "Every run starts with a question you can't answer yet." / "Feed it everything; it will tell you what matters." / "A task without a lock is a collision waiting to happen." / "The spec is a promise — read it before you make one." / "Before the first line compiles, the brief must." / "Wake the machine; give it something real to chew on." / "Context is the only thing that separates signal from noise." / "The job isn't real until it's written down." / "Lock it or lose it." / "Derive what you can; flag what you can't." / "Read the brief twice; build once." / "An untyped task is a guess with a deadline." / "Normalize the noise before you chase the signal." / "Wake up, Neo — the work has found you."

BASELINE banner (stage offset 2):
```
  ╭─ ⌐■-■  BASELINE · 2/9 · THE GUARDIAN · auto
  │  "[quote from BASELINE pool]"
  ╰─
```
BASELINE pool (14): "Never build a fix on a broken tree." / "Green at the start, green at the end — or you fixed nothing." / "A red baseline is not your bug to own." / "Fetch first; stale refs have ended careers." / "The suite tells no lies if you ask it correctly." / "Trust the test run you ran, not the one you remember." / "A clean branch is the only safe foundation." / "If it was already broken, say so and stop." / "The ground must be solid before you add a floor." / "Run it now, so you can prove it later." / "Prove the floor before you trust the floor." / "A baseline you didn't run is a baseline you don't have." / "Inherit no failure you did not cause." / "Measure on green so you can prove on red."

PLAN banner (stage offset 3):
```
  ╭─ ⌐■-■  PLAN · 3/9 · THE ARCHITECT · opus/high
  │  "[quote from PLAN pool]"
  ╰─
```
PLAN pool (14): "Design twice, so reality only has to happen once." / "The most dangerous flaw is the one the blueprint calls a feature." / "What you do not name in the plan will name itself in production." / "Scope is a fire: contain it or feed it." / "Every line you don't write is a line you never debug." / "Decide the hard things on paper, where erasing is cheap." / "The shape of the solution hides in the shape of the problem." / "Cut the scope until it bleeds, then ship the part that lived." / "A blueprint nobody questions is a blueprint nobody read." / "Denial is the most predictable of all human responses." / "The blueprint is cheaper than the rebuild." / "Name the blast radius before it names you." / "A plan survives contact only if it expected the contact." / "I can only show you the door; the plan is how you walk through it."

PLAN GATE banner (stage offset 4):
```
  ╭─ ⌐■-■  PLAN GATE · 4/9 · THE ORACLE · <review_model>/xhigh
  │  "[quote from PLAN GATE pool]"
  ╰─
```
PLAN GATE pool (14): "The flaw hides in the part everyone agreed not to question." / "A question carries more weight than any answer it returns." / "The map is not the territory, and the demo is not the system." / "Ask what it costs before you ask what it does." / "The second pair of eyes sees the assumption the first pair made." / "Improve the plan, not the planner's feelings." / "A good review changes the plan; a great one changes the question." / "Disagree on paper now, or apologize in the incident channel later." / "The cheapest place to be wrong is before the first commit." / "Trust the plan less than the reasons behind it." / "The plan you can't defend on paper won't survive the diff." / "Refute it now, while erasing is free." / "A criterion with no step is a promise with no plan." / "There is no shortcut past the review."

RED banner (stage offset 5):
```
  ╭─ ⌐■-■  RED · 5/9 · THE SABOTEUR · auto
  │  "[quote from RED pool]"
  ╰─
```
RED pool (14): "A test that can't fail tells you nothing." / "Write the failure first; let success prove itself." / "Red is honest; green is a hypothesis." / "The test you skip is the bug you ship." / "If it doesn't break, it doesn't test." / "Encode the crime before you solve it." / "Freeze the witness before the suspect can coach them." / "A hollow red is worse than no red at all." / "The assertion must sting — or it's decoration." / "Lock the test before you write the fix." / "A green you didn't earn is a lie you'll inherit." / "Make it fail for the reason you claim it fails." / "An import error is a no-show, not a witness." / "Break it on purpose, or production breaks it for you."

IMPLEMENT banner (stage offset 6):
```
  ╭─ ⌐■-■  IMPLEMENT · 6/9 · NEO · sonnet/medium
  │  "[quote from IMPLEMENT pool]"
  ╰─
```
IMPLEMENT pool (14): "Make it small enough to be wrong cheaply." / "Touch only what the plan told you to touch." / "One reviewable step beats ten clever ones." / "The first version should be obvious, not impressive." / "Done is a diff someone else can understand." / "I know kung fu." / "There is no spoon." / "Don't think you are; know you are." / "Free your mind." / "He is beginning to believe." / "Change the diff, not the mandate." / "Small enough to revert is small enough to trust." / "The plan is the path; walk it, don't wander." / "Stop trying to be clever and be correct."

DIFF GATE banner (stage offset 7):
```
  ╭─ ⌐■-■  DIFF GATE · 7/9 · AGENT SMITH · <review_model>/xhigh
  │  "[quote from DIFF GATE pool]"
  ╰─
```
DIFF GATE pool (14): "Read the diff as if your worst enemy wrote it." / "Your green tests are a comfort, not a verdict." / "Approve nothing you would not be paged for at midnight." / "The bug you cannot find is the one you decided was not there." / "Every assumption is a door you left unlocked." / "Find the failure before the failure finds the user." / "Mr. Anderson." / "That is the sound of inevitability." / "Never send a human to do a machine's job." / "You are a plague, and I am the cure." / "Green is not innocence; it is an alibi to check." / "The diff you wave through is the page you write at 3 a.m." / "Trust the merit, never the headcount." / "Inevitability, Mr. Anderson — the bug you chose not to see."

SHIP banner (stage offset 8):
```
  ╭─ ⌐■-■  SHIP · 8/9 · THE ONE · auto
  │  "[quote from SHIP pool]"
  ╰─
```
SHIP pool (14): "Draft only. The human merges." / "A branch, a PR, a verdict — that's the job." / "Ship the evidence, not the confidence." / "The record is the PR; the scratch is disposable." / "Open the door; let the human walk through it." / "Push the branch, not the merge." / "Every good run ends with a diff someone can approve." / "The draft is honest about what it is." / "Done means reviewable, not merged." / "Raise your hand when you're finished — don't merge yourself." / "One clean commit; one honest history." / "Squash the noise; keep the story." / "The branch is yours; the merge is theirs." / "I came to hand you the key, not to turn it."

REPORT banner (stage offset 9):
```
  ╭─ ⌐■-■  REPORT · 9/9 · THE MESSENGER · auto
  │  "[quote from REPORT pool]"
  ╰─
```
REPORT pool (14): "The result is only as good as the evidence behind it." / "State the outcome; show your work." / "A structured report is a gift to the next person in the chain." / "Name the blockers before the blockers name you." / "The human needs the map, not just the destination." / "Criteria in; evidence out." / "If you can't report it clearly, you don't understand it yet." / "The PR is the answer; the report is the reasoning." / "Leave breadcrumbs: someone will need to retrace this." / "End with the truth, whatever it is." / "A metric unrecorded is a lesson unlearned." / "Say what shipped, what slipped, and why." / "The next operator reads what you leave behind." / "End with evidence, not optimism."

Quote selection rule (same deterministic formula as other commands): N = number of characters in
task-id; stageOffset = stage offset printed in banner above (1–9); rework_round =
`rework_round:` value in state.md (0 at first pass); quote = 0-based item at index
(N + stageOffset + rework_round) mod M, where M = pool size (count list from 0). Read fresh
from state.md each time. Do NOT pick at random; do NOT default to first.

---

1. INGEST — set up the run. All setup before printing the INGEST banner.

   a. Ensure `feature-research/` is in `.gitignore`: if line `feature-research/` absent,
      append it. (Same guard as `start.md` step 1 — scratch must not land in PR diff.)

   b. Derive task directory path: `feature-research/<task-id>/`.

   c. Run lock check: if `feature-research/<task-id>/state.md` already exists and contains
      `mode: auto` AND stage is not `done` or `aborted`, print:
      ```
      ■ LOCKED · a run for task-id '<task-id>' is already active (stage: <stage>).
        Abort the existing run first (set stage: aborted in state.md) or wait for it to complete.
      ```
      Then STOP. Re-trigger after done/aborted may start fresh.

   d. Create `feature-research/<task-id>/` directory if absent.

   e. Seed `feature-research/<task-id>/state.md` with the exact STATE block (byte-faithful:
      column-0 `key:`, no markdown bullets or bold, STATE:START/STATE:END markers):
      ```
      # Pipeline state
      <!-- STATE:START -->
      task:                <task-id>
      stage:               ingest
      gate:                none
      iteration:           0
      max_iterations:      3
      exit_rule:           full suite green, no new failures vs baseline, frozen test unchanged, diff within scope
      plan_verdict:        pending
      diff_verdict:        pending
      mode:                auto
      task_id:             <task-id>
      source_url:          none
      repos:               current
      branch:              anderson/auto/<task-id>-<slug>
      baseline:            pending
      test_cmd:            none
      test_cmd_confidence: none
      criteria_confidence: none
      frozen_test:         none
      frozen_test_hash:    none
      rework_round:        0
      open_findings:       0
      plan_panel:          pending
      diff_panel:          pending
      ci_status:           pending
      ci_conclusion:       none
      red_reason:          none
      tier:                pending
      review_model:        opus
      panel_model:         pending
      reviewers:           0
      arbiter:             none
      arbiter_trigger:     none
      replan_bounced:      no
      budget_state:        ok
      override:            none
      open_questions:      0
      <!-- STATE:END -->

      ## Done so far

      ## Still open

      ## ❓ Open questions
      ```
      Where `<slug>` = title lowercased, spaces replaced with hyphens, truncated to 30 chars.
      Set `review_model:` to `fable` if the `--fable` flag was parsed from $ARGUMENTS, else `opus`.
      If file already exists (re-run after abort), overwrite with this fresh block.

   f. Parse body/acceptance_criteria: if body present, scan for an "acceptance criteria",
      "acceptance_criteria", or "criteria" section; extract criteria if found; set
      `criteria_confidence: high` in state.md. If body absent or no criteria section found,
      derive criteria from title + body by best judgement and set
      `criteria_confidence: low` in state.md. Record derived criteria under `## Done so far` in
      state.md as bullet list prefixed `[criteria]`.

   g. Parse SOURCE LINK and REPO scope from the TaskSpec (body or @file):
      - `source_url:` — if TaskSpec carries a source-task URL (Linear/GitHub/Jira/etc. ticket
        link) or a bare id you can resolve to one, record as `source_url:` in state.md. Rendered
        at TOP of PR body so reviewer can trace work to its ticket. If absent,
        leave `source_url: none` (PR body omits the link — never invent one).
      - `repos:` — set of repos this task must change. Default `current` (repo you are in).
        Set to comma-list when work spans repos: TaskSpec names additional `repos:`, OR
        scope_paths / plan point outside this repo, OR project memory / `CLAUDE.md` records a
        sibling repo this task must touch. Record as `repos: <current>[,<repo2>,...]`. Multi-repo
        runs handled in BASELINE (isolation) + SHIP (one branch + PR per repo).
      - DESIGN — if the TaskSpec references a design (figma.com URL, image path, image attached
        to the source ticket), normalize it into `feature-research/<task-id>/design/`: Figma →
        MCP `get_screenshot` (+ `get_design_context` for exact strings); ticket attachment →
        download it; local path → copy it. Then write `design/inventory.md`: every EXACT text
        string (quoted character-faithful), every state/variant, layout facts. The planner
        turns inventory lines into `source: design` criteria; the diff panel compares the built
        UI against these files. No human to ask in auto — capture impossible → note it under
        `## Done so far` and the affected criteria downgrade to `manual` proof.

   h. (BANNER RULE) Print the INGEST banner now, last line before any further action.

   i. Report INGEST complete in state.md `## Done so far`.

2. BASELINE — verify repo is green before any change.

   a. Update state.md: set `stage: baseline`.

   b. Run `git fetch` for latest refs.

   c. Determine default branch name: `git symbolic-ref refs/remotes/origin/HEAD` or inspect
      `git branch -r` for `origin/HEAD`.

   d. Workspace isolation — clean, isolated checkout per repo so this run never disturbs
      in-flight work and concurrent runs can't collide. Branch name (each repo): `anderson/auto/<task-id>-<slug>`.
      - SINGLE repo (`repos: current`): if working tree DIRTY, do NOT branch in place (would
        entangle someone's uncommitted work) — instead create isolated **git worktree** off
        latest default and operate there:
        `git worktree add -b anderson/auto/<task-id>-<slug> ../.anderson-auto/<task-id> origin/<default-branch>`,
        then run all subsequent steps from that worktree path. If tree CLEAN, normal
        `git checkout -b anderson/auto/<task-id>-<slug> origin/<default-branch>` is fine.
      - MULTI repo (`repos:` lists more than `current`): for EACH repo in list, create isolated
        worktree (preferred — fast, shares object store) or fresh clone if no local checkout
        exists, branch off that repo's latest default, record its path. NEVER edit another repo's
        primary checkout in place. Record per-repo branch + worktree path under `## Done so far`.
      - Clean up worktrees on terminal path: after SHIP/abort, `git worktree remove` each one
        (branch + PR are the durable record). Update `branch:` in state.md with resolved name.

   e. Resolve `test_cmd`:
      - If TaskSpec body or @file contains a `test_cmd:` field, use it directly and set
        `test_cmd_confidence: high`.
      - Otherwise infer from repo conventions: check for `pytest.ini`, `setup.cfg [tool:pytest]`,
        `pyproject.toml [tool.pytest.ini_options]` → infer `python -m pytest`; check for
        `package.json` with a `test` script → infer `npm test`; check for `Makefile` with a
        `test` target → infer `make test`; check for `go.mod` → infer `go test ./...`.
      - Set `test_cmd_confidence: high` if one clear match, `low` if ambiguous (multiple matches
        or partial signals), `none` if nothing found.
      - If `test_cmd_confidence: none` (completely un-inferable): write structured report to
        `feature-research/<task-id>/report.md`:
        ```
        ## Auto-mode abort: needs-spec
        reason: test_cmd could not be inferred from repo conventions
        task_id: <task-id>
        branch: <branch>
        ```
        Set state.md `stage: aborted`, print the needs-spec report, and STOP.
      - Record `test_cmd:` and `test_cmd_confidence:` in state.md.

   f. (BANNER RULE) Print the BASELINE banner now.

   g. Run resolved `test_cmd`. Capture output. If suite RED (non-zero exit):
      write structured report to `feature-research/<task-id>/report.md`:
      ```
      ## Auto-mode abort: baseline-broken
      reason: baseline test suite is red — cannot fix on a broken tree
      task_id: <task-id>
      branch: <branch>
      test_cmd: <test_cmd>
      output: <first 40 lines of test output>
      ```
      Set state.md `stage: aborted`, `baseline: broken`, print the report, and STOP.
      If GREEN: set `baseline: green` in state.md. Record in `## Done so far`.

3. PLAN — invoke the planner to draft plan.md.

   a. Update state.md: set `stage: plan`.

   b. (BANNER RULE) Print the PLAN banner now, last line before invoking the planner.

   c. Invoke the **planner** subagent, seeded with:
      - task title and body
      - derived acceptance_criteria (from state.md `## Done so far` `[criteria]` bullets —
        planner expresses them in plan.md `## ✅ Acceptance criteria`: `source: ticket` when
        `criteria_confidence: high`, `derived` when low)
      - criteria_confidence (so planner notes low-confidence derivations)
      - the `design/` path when step 1g captured one (→ `source: design` criteria)
      - scope_paths if present in the TaskSpec
      Planner writes `feature-research/<task-id>/plan.md`.

   d. Update state.md: set `stage: confidence_gate`. Record in `## Done so far`.

   3a. CONFIDENCE GATE — assess planner's confidence in the task.

   e. Read `feature-research/<task-id>/plan.md`. Read the `## 📈 Scorecard` section.
      Find the Confidence row. If planner's Confidence score ≤ 3 (ambiguous,
      underspecified, or out-of-scope):
      RELAXED in auto mode (Override Policy) — do NOT abort. Record
      `low planner confidence (<score>) — proceeding under override` under `## Done so far`, append
      `low-confidence` to the `override:` field in state.md (metric reference for this relaxation;
      comma-joined if more relaxations fire later), set flag to add the `needs-human` label at
      SHIP (step 8c), and CONTINUE. Diff gate's RED test + CI veto + blind panel remain the safety
      net for an under-specified task.
      (Previously: this aborted with a needs-spec report when Confidence ≤ 3.)
      If Confidence > 3: continue normally.

   3b. ROUTE — compute difficulty tier (drives plan-gate depth, diff panel size, and arbiter
       policy). Difficulty routing means a one-line fix does not pay for a four-agent panel.

   f. Read the `## 📈 Scorecard` Planner column: Risk, Coupling, Confidence, Testability. Compute
      the INITIAL tier (first match wins, top-down):
        - CRITICAL — Risk ≥ 9 OR Testability ≥ 7 (the scorecard anchor "needs a human/manual
                     tester" — cannot be verified autonomously).
        - HARD     — Risk ≥ 7 OR Coupling ≥ 7 OR Confidence ≤ 4.
        - TRIVIAL  — Risk ≤ 2 AND Coupling ≤ 3 AND Confidence ≥ 8.
        - NORMAL   — anything else (default).
      Record `tier: <trivial|normal|hard|critical>` in state.md. This tier is PROVISIONAL — step 7d
      re-tiers against actual diff size and takes the MAX (tier can only escalate, never drop).

4. PLAN GATE — criteria-coverage check + ONE plan-reviewer (skipped for a TRIVIAL tier). Plan errors
   are cheap to fix (rework; nothing ships), so this side stays light — rigor budget is
   spent at the diff gate.

   a. Update state.md: set `stage: plan_gate`, `plan_panel: pending`.

   b. Acceptance-criteria coverage check (mechanical): for each criterion derived/given in step 1,
      verify at least one `## 🛠 How` step in `plan.md` maps to it. Collect unmapped criteria as
      blocking findings.

   c. TRIVIAL shortcut: if `tier: trivial` AND no unmapped criteria → set `plan_panel: clear` (a
      trivial plan does not earn a reviewer) and continue to step 5.

   d. (BANNER RULE) Print the PLAN GATE banner now, last line before invoking the plan-reviewer.

   e. Invoke ONE **plan-reviewer** subagent (model override = state.md `review_model`, effort xhigh)
      with a refute posture: "Refute this plan — find why it
      fails, misses an acceptance criterion, or under-counts the blast radius; default to reject
      (`fix_first`) if uncertain. Make inline fixes (your normal mode). Append your report under
      `## 🔭 Review`. Set `plan_verdict` in state.md." Seed it with the unmapped criteria from 4b.

   f. Read `plan_verdict`:
      - `ship` AND no unmapped criteria → set `plan_panel: clear` and continue to step 5.
      - `fix_first` OR unmapped criteria remain → ONE bounded plan-rework: invoke the **planner**
        again with the specific blockers, then re-run the plan-reviewer once. Still not `ship` →
        set `plan_panel: rejected`, abort (`stage: aborted`, reason `plan-rejected`), print, STOP.
      - `regrill` → needs human decisions auto mode cannot make: set `plan_panel: needs-human`,
        abort (`stage: aborted`, reason `plan-needs-human`), print, STOP.

   g. CAPTURE OPEN QUESTIONS — auto has no grill, so ambiguities the gated loop would resolve
      with a human are recorded here and surfaced in the PR instead of silently guessed. Read
      the now-final `plan.md` "🧯 Error handling" + "✅ Decisions". Record under state.md
      `## ❓ Open questions`, one line each:
      - `[open] <failure path / question> — <why it needs a business call auto can't make>` for every
        `needs-context` row and every unresolved open question in "✅ Decisions".
      - `[answered] <question> → <answer> (<basis>)` for ambiguities auto resolved on its own — each
        `deduced` error path's chosen handling, derived acceptance criteria when
        `criteria_confidence: low`, and the low-confidence planner override (step 3a) if it fired.
      Set `open_questions: <count of [open] lines>` in state.md. Non-zero count forces the
      `needs-human` label at SHIP (step 8c) — auto must not invent a business answer it lacks context
      for; it ships the question to the human.

5. RED — write failing test encoding the acceptance criteria, confirm it fails for the right
   reason, then freeze it.

   a. Update state.md: set `stage: red`.

   b. (BANNER RULE) Print the RED banner now, last line before the RED step begins.

   c. Using your Write tool, write a failing test file under the repo's test directory that:
      - Encodes the acceptance criteria from step 1
      - Will fail with a meaningful assertion error (not an import/syntax error)
      - Is a single self-contained test file
      Record the test file path as `<frozen_test_path>`.

   d. Run the test to confirm RED: `<test_cmd> <frozen_test_path>` (or equivalent
      single-file filter). Capture BOTH exit code and output, then classify the failure
      (red-for-right-reason auto-check):
      - GENUINE RED — non-zero exit AND output shows a real ASSERTION failure for the new test
        (`AssertionError`, a pytest `assert` diff, `Error: expect(...)`, JUnit
        `AssertionFailedError`, a Go `--- FAIL` with a checked condition, etc.). Set
        `red_reason: genuine` in state.md and proceed to 5e.
      - HOLLOW RED — non-zero exit but failure is a LOAD/COLLECTION error, not an assertion:
        scan output for `SyntaxError`, `ImportError`, `ModuleNotFoundError`, `NameError` at
        collection, pytest `errors` / `collected 0 items` / `INTERNALERROR`, `cannot find module`,
        or a build/compile error, with NO assertion failure present. A test that errors is not a
        red test. Set `red_reason: hollow`, then ONE bounded rewrite: fix only the
        import/syntax/collection fault (keep SAME assertion intent) and re-run.
        - If GENUINE RED on retry → set `red_reason: genuine` and proceed.
        - If still HOLLOW → abort. Write `feature-research/<task-id>/report.md`:
          ```
          ## Auto-mode abort: hollow-red
          reason: the RED test errors (import/syntax/collection) instead of failing an assertion
          task_id: <task-id>
          frozen_test: <frozen_test_path>
          last_error: <the key error line from the output>
          ```
          Set `stage: aborted`, print the report, and STOP.
      - UNEXPECTED GREEN — exit 0: criteria may already be met. Record anomaly in
        `## Done so far`, set `red_reason: green`, proceed anyway (diff gate confirms).

   e. Freeze the test: record `frozen_test: <frozen_test_path>` in state.md.
      Capture content hash: run `git hash-object <frozen_test_path>`, record output
      as `frozen_test_hash: <hash>` in state.md. This snapshot is the tamper baseline.

   f. Record in `## Done so far`.

6. IMPLEMENT — invoke the implementer to make the red test green.

   a. Update state.md: set `stage: implement`.

   b. (BANNER RULE) Print the IMPLEMENT banner now, last line before invoking the implementer.

   c. Invoke the **implementer** subagent: execute `feature-research/<task-id>/plan.md`;
      make the frozen test pass; fill the Evidence column of plan.md `## ✅ Acceptance
      criteria` (per its agent instructions); write `feature-research/<task-id>/audit.md`.
      Implementer also runs a self-review pass before the diff gate (cheap; cuts panel rounds).
      Set stage=diff_gate after invocation.

7. DIFF GATE — CI veto + tier-sized blind reviewer panel + arbiter-on-split.
   Order is deliberate: free objective gate (CI) runs FIRST and short-circuits a red build before
   any reviewer tokens are spent; panel size scales with `tier`; arbiter runs only when the
   panel splits (or tier is critical).

   a. Update state.md: set `stage: diff_gate`, `diff_panel: pending`, `arbiter: none`.

   b. Test-tamper guard: run `git hash-object <frozen_test>` (path from state.md).
      Compare to `frozen_test_hash:` from state.md.
      If hashes differ OR file no longer exists: tamper event — immediately
      abort with a `needs-human` report:
      ```
      ## Auto-mode abort: needs-human (test tamper detected)
      reason: frozen test was modified or deleted after RED step
      task_id: <task-id>
      frozen_test: <frozen_test_path>
      hash_at_red: <frozen_test_hash>
      hash_now: <current_hash>
      ```
      Set `stage: aborted`, print the report, and STOP.

   c. CI / suite veto. CI is a VETO, not a vote — a red build or suite fails the gate regardless
      of reviewer votes. The one gate the model cannot talk its way past.

      i. Baseline-comparison run (ALWAYS): run the full suite in-tree `<test_cmd>`; capture exit
         code and output. Baseline was GREEN at step 2, so any failure here is new. Before
         trusting a red, re-run a single suspected-flaky failing test once — a test that then
         passes is a flake, not a regression; note it, do not count it.

      ii. Authoritative CI veto (WHEN AVAILABLE): if repo has GitHub Actions CI
          (a `.github/workflows/*.yml` triggered on `push` or `pull_request`) AND a remote exists
          (`git remote` is non-empty) AND `gh auth status` succeeds:
            - Push run branch to trigger CI: `git push -u origin <branch>` (branch-only and
              safe; SHIP re-pushes final state — see step 8e).
            - Await the run for the pushed head SHA: poll
              `gh run list --branch <branch> --limit 1 --json status,conclusion,headSha,databaseId`
              until `status` is `completed` (or `gh run watch <databaseId> --exit-status`). Bound
              the wait by the per-run time budget — if it blows, set `budget_state: blown`,
              treat as CI fail.
            - Set `ci_status: gh-actions` and `ci_conclusion: <success|failure|cancelled|timed_out>`.
              Anything other than `success` fires the CI VETO (gate FAILS → rework, step 7h).
      iii. Fallback: if GH Actions / remote / `gh` unavailable, the in-tree run from (i) IS
           the veto. Set `ci_status: in-tree (fallback)` and `ci_conclusion: pass|fail`, note
           the fallback under `## Done so far` (surfaces in PR body + final report).

      iv. SHORT-CIRCUIT: if CI/suite veto FAILED (`ci_conclusion` not `success`/`pass`), a red
          build is dispositive — do NOT run the reviewer panel (no tokens on a known-bad diff). Set
          `diff_panel: ci-veto` and go straight to the rework loop (step 7h).

   d. Scope / forbidden-path guard + RE-TIER. Measure diff against branch base with
      `git diff --name-only` and `git diff --stat`; record files-changed and lines-changed
      (added+deleted). Each RELAXED guard below that fires appends its tag to the `override:`
      field in state.md (comma-joined) — that field is this step's metric reference, surfaced in the
      `metrics:` line so a relaxed run is greppable.
      - MIGRATIONS (HARD STOP — Override Policy rule 1) — if any changed file is a DB migration
        (`*/migrations/*`, or the repo's migration directory/format), auto has violated a
        non-negotiable rule: it must NEVER author a migration. Discard the change, write a
        `needs-migration` hand-off report to `feature-research/<task-id>/report.md`, set
        `stage: aborted` (abort surfaces as `outcome=ABORTED:needs-migration` in the metrics
        line — the metric reference for the migration guard), print it, and STOP.
      - OTHER SENSITIVE / DEPENDENCY paths (RELAXED — Override Policy) — `.github/`, `*.yml` in
        `.github/`, CI config, `*.lock`, `package-lock.json`, `yarn.lock`, `Pipfile.lock`, dependency
        manifests, or secrets-like paths (`.env`, `*.pem`, `*.key`): auto MAY change these when the
        task requires it. Attach `needs-human` label as heads-up AND force `tier: critical`
        (extra scrutiny), record flagged paths, append `sensitive-paths` to `override:` — but do
        NOT abort and do NOT fail the gate.
      - SCOPE (RELAXED — Override Policy) — if scope_paths was provided and changed files fall outside
        it: record out-of-scope files, append `scope` to `override:`; do NOT fail the gate.
      - RUNAWAY (RELAXED — Override Policy) — if diff exceeds 200 lines OR 20 files: record
        size as NOTE, append `runaway` to `override:`; do NOT fail the gate (panel + CI still
        judge the diff on merit).
      - RE-TIER on actual diff size, taking the MAX with the current tier (tier only escalates):
          · diff LARGE (≥150 lines OR ≥8 files) → at least HARD
          · diff SMALL (≤40 lines AND ≤2 files) → does NOT lower the tier (max rule)
        Set `tier:` = max(current tier, diff-derived tier); a forbidden/dep hit pins it to CRITICAL.

   e. (BANNER RULE) Print the DIFF GATE banner now, last line before the panel runs.
      Print it ONCE for the whole panel — not per reviewer.

   f. Run the blind reviewer panel — SIZE IT BY `tier`:
        - TRIVIAL  → 1 reviewer:  correctness
        - NORMAL   → 2 reviewers: correctness, regressions+security
        - HARD     → 3 reviewers: correctness, regressions+security, plan-match
        - CRITICAL → 3 reviewers: same as HARD (escalation past HARD is always-arbiter + the
                     mandatory `needs-human` label, NOT more reviewers — a 4th lens just duplicates).
      Lenses:
        · correctness          — "Does the diff do what the task asks, correctly, with no logic bug
                                  or unhandled case? Is every `deduced` row in the plan's 🧯 Error
                                  handling table actually handled in the diff? Is every row of
                                  plan.md `## ✅ Acceptance criteria` PROVEN by its Evidence —
                                  run the test, open visual pairs (design/ vs evidence/), run
                                  scratch e2e; blank or hollow evidence = fix_first?"
        · regressions+security — "What does this break elsewhere, and what does it expose (input
                                  handling, secrets, injection, auth)?"
        · plan-match           — "Does the diff match `plan.md` — nothing more (scope creep), nothing
                                  less (a missed step)?"
      Record `reviewers: <n>`. Run panelists IN PARALLEL — emit all N **reviewer** invocations in
      a SINGLE message (one Agent call each). Parallel is safe here ONLY because each panelist writes
      to its OWN file and returns its verdict in its reply — no shared `plan.md` / `diff_verdict`
      writes to collide (why the plan gate stays sequential and this one does not). Frame each:
        "You are reviewer <i>/<n> on the auto-mode diff panel. Lens: <lens>. You are BLIND: judge from
         the scoped diff + `plan.md` + the task ONLY. Do NOT read `audit.md` and do NOT read any other
         review file — independence is the point. Refute the diff through your lens; default to reject
         (`fix_first`) if uncertain. Write your review ONLY to
         `feature-research/<task-id>/review-<lens>-r<round>.md` (do NOT touch plan.md or state.md).
         End your final message with exactly two lines: `VERDICT: ship|fix_first` and
         `FINDINGS: <count of blocking findings>`."
      MODEL TIERING (where the harness supports a per-invocation model override): size panelist
      model to tier — run TRIVIAL and NORMAL panelists on a faster/cheaper tier (sonnet), run
      HARD and CRITICAL panelists on the reviewer default (state.md `review_model`/xhigh — `opus`,
      or `fable` under `--fable`), since a missed bug at those tiers has real blast radius and a
      stronger reviewer earns its cost there. Arbiter ALWAYS runs at the reviewer default
      (`review_model`/xhigh) regardless of tier. If no override available, all panelists run at the
      reviewer default — model tiering is a cost optimization, not a correctness requirement. Record
      the model the panel actually ran on as `panel_model: <sonnet|opus|fable>` in state.md
      (the reviewer-default value when no override available and all panelists fell back to it) —
      this is step 7f's metric reference, surfaced in the `metrics:` line.
      Collect each panelist's `VERDICT` + `FINDINGS` from its reply; record one
      `- diff_vote_<lens>: <verdict> (<findings>)` line under `## Done so far`.

   g. Resolve the gate (CI already passed — a red build short-circuited at 7c-iv and never reaches
      here). Count a `fix_first` as a refute. Arbiter is the reviewer-default quality gate over the
      panel (runs at `review_model`/xhigh) — runs on every outcome EXCEPT a unanimous refute:
        - SPLIT — panel NOT unanimous (mix of ship and fix_first) → arbiter runs to resolve
          contested findings. Set `arbiter_trigger: split` in state.md.
        - UNANIMOUS SHIP — all panelists ship → arbiter ALWAYS runs as final sign-off over
          the panel. It does NOT rubber-stamp: independently re-reviews the diff and tries to find
          the one objection the panel missed. Safety net for a panel that agreed too
          easily — especially a cheaper sonnet panel on a trivial/normal tier. Set
          `arbiter_trigger: unanimous-ship` (or `critical` when tier is critical) in state.md.
        - UNANIMOUS REFUTE — all panelists fix_first → gate FAILS, no arbiter runs (nothing to debate)
          → set `arbiter_trigger: none` and go to rework (7h).
      (`arbiter_trigger` is step 7g's metric reference — records WHY the arbiter ran, surfaced in
      the `metrics:` line — distinct from `arbiter`, which records its verdict.)
      When arbiter runs: invoke ONE **reviewer** subagent as the ARBITER (read-only; model override
      = state.md `review_model`, effort xhigh), given the diff + `plan.md` + task + ALL panel review
      files. Frame it:
        "You are the ARBITER. Either the panel split, this is a critical task, or the panel
         unanimously shipped and you are the final sign-off. Read every review file and the diff.
         If there are contested findings, resolve each ON MERIT, not on headcount: a lone correct
         reviewer outranks two wrong ones. If the panel was unanimous, do NOT rubber-stamp —
         independently re-review the diff and actively look for the strongest objection the panel
         missed. You MUST emit an `## Options considered` table BEFORE your verdict:
           | Option | + (pro) | − (con) | Score | Verdict |
         with AT LEAST two rows (e.g. `ship as-is`, `rework finding X` — on a clean unanimous ship the
         second row is the strongest objection you can construct, even if you ultimately reject it) — a
         single-row table is a defect; redo it. Every rejected option must state why it is worse than
         the chosen one. Default to reject if uncertain. End with `ARBITER: ship|fix_first`."
      Record `arbiter: <ship|fix_first|none>` (`none` only on a unanimous refute, where no arbiter ran).
      GATE PASSES if: arbiter returned `ship` (it runs on every split and every unanimous ship) —
      AND tamper guard passed. (Scope / forbidden / dependency / runaway findings only attach the
      `needs-human` label or a note in auto mode — see Override Policy — they do NOT fail the gate.)
      GATE FAILS → rework (7h) if: arbiter returned `fix_first`, OR panel unanimously refuted
      (no arbiter ran).
      Set `diff_panel: <pass | killed-by-arbiter | killed-by-vote>`.
      Consolidate per-lens review files (+ arbiter's, if any) into `plan.md`'s `## 🔭 Review`
      as `### Diff review — <lens> (round <n>)` subsections — the durable PR record.

   h. On GATE FAIL — rework. CLEAN UP the round, then re-enter at the PANEL (NOT step 1):
      i. Per-round reset: set `diff_verdict`/`arbiter` back to pending (per-lens review files
         already round-stamped `-r<round>`); prune "Still open" to ONLY the unresolved blocking
         findings — the implementer's instructions for this round.
      ii. Increment `rework_round:`. Read prior `open_findings:`. Count this round's blocking
          findings (panel + arbiter).
      iii. NON-CONVERGENCE check — if findings did NOT shrink vs prior round
           (count >= previous AND `rework_round > 1`) OR a finding RECURS identically across rounds,
           implementer is not converging → APPROACH problem, not a local bug:
           - REPLAN BOUNCE (once): if `replan_bounced: no`, set it `yes`, route back to PLAN — invoke
             the **planner** with the panel/arbiter's standing objection to choose a DIFFERENT
             approach (planner MUST emit an `## Options considered` table — ≥2 approaches with
             +/− and a justified pick over the rejected ones), then resume at step 6 (IMPLEMENT) with
             the fresh plan. Re-freezing the RED test not needed (criteria unchanged).
           - If `replan_bounced: yes` already: give up cleanly — abort with a `needs-human` report
             (`stage: aborted`, reason `no-convergence`, list the recurring findings), print, STOP.
           Otherwise (findings shrinking normally): continue to iv.
      iv. Budget: if `rework_round > max_iterations` → abort (`stage: aborted`, reason `budget`).
      v. Otherwise: update `open_findings:`, invoke the **implementer** again (fix ONLY "Still open"),
         then re-enter the diff gate at step 7b — tamper guard + CI veto (re-push → re-await) +
         tier-sized panel all re-run on the new diff. Bounded by max_iterations.

8. SHIP — push branch and open a draft PR.

   a. Update state.md: set `stage: ship`.

   b. (BANNER RULE) Print the SHIP banner now, last line before the ship step.

   c. Determine labels: always add `auto-mode`. Add `needs-human` if sensitive/dependency paths
      flagged (step 7d) OR planner confidence was ≤ 3 (step 3a, relaxed under the Override Policy) OR
      `open_questions > 0` (step 4g — unresolved business-context questions need a human) OR
      multi-repo run (cross-repo is higher-risk by default).

   d. Build the PR body — the whole plan MINUS the how: 🛠 How and ✅ Decisions are DELIBERATELY
      excluded (the diff IS the how — don't double it up). An EMPTY section is OMITTED, never
      printed as "none" filler. Normal (open) sections first, the reference/audit collapses last.
      Structure, in this order:

      1. SOURCE — if `source_url` is set, the first line is `Source: <source_url>` (the ticket this
         traces to; weave any ticket context in as background). Omit the line when
         `source_url: none` — never fabricate one.

      2. `## 🎯 What & why` (2–4 lines) — lifted from plan.md `## 🎯 What` / `## 🤔 Why`.

      3. `## ✅ Acceptance criteria` — the plan.md table verbatim, Evidence column filled.
         Scratch dies at ship, so rewrite scratch-path evidence: visual cells →
         `visual: verified at gate` (+ the design source link when one exists); scratch-e2e
         cells → `e2e: verified at gate (ephemeral, deleted at ship)`; any `promote candidate`
         e2e → one bullet under the table naming the flow worth a permanent test. Under the
         table, two lines:
         `test: <test_cmd> · frozen: <frozen_test>`
         `Validated: plan-gate <plan_panel> · diff-panel <diff_panel> · arbiter <arbiter> · CI <ci_conclusion>`

      4. `## 🗺 Design` — the plan.md 🗺 Design body shown normally (lift it OUT of the plan's
         `<details>` collapse). Omit when the design was a single trivial line already implied by What.

      5. `## 🧪 How to test` — reviewer-facing, from audit.md `## ⚙️ Setup & test`: the test
         command to run, plus step-by-step for any `manual`-proof criteria. Then a
         `**Config required:**` line — new env vars / flags / dependencies / data setup
         (env-var labels and so forth) — ONLY when audit.md + the diff introduce one; omit when
         none. (Auto never authors migrations — if one were needed it has already aborted at 7d.)

      6. `## 🔴 Open questions` (from state.md `## ❓ Open questions`, step 4g) — ONLY when
         `[open]` lines exist: each as `- <question> — <why it needs context>`. These are the
         business calls auto declined to invent — the reviewer must answer them. The
         `[answered]` assumptions move to the Verification collapse (item 10).

      7. `<details><summary>📈 Scorecard</summary>` — the plan.md Scorecard table verbatim
         (Planner + Reviewer columns).

      8. `<details><summary>💥 Blast radius</summary>` — the plan.md 💥 Blast radius table.

      9. `<details><summary>🧯 Error handling</summary>` — the plan.md 🧯 Error handling table.

      10. `<details><summary>Review & verification</summary>` — condensed:
         `tier <tier> · reviewers <n> · arbiter <arbiter> · rework rounds <r> · red <red_reason>`,
         the per-lens `diff_vote_<lens>` verdicts on one line, and auto's assumptions — each
         `[answered]` line as `- <question> → <answer> (<basis>)` (verify before merge — they
         are deductions, not confirmed product decisions).

      11. `<details>Audit & risks</details>` — collapse the long tail: audit.md summary (files
         changed), residual risks, labels applied, and the machine-greppable metrics line:
         `metrics: tier=<t> panel_model=<m> reviewers=<n> arbiter=<v> arbiter_trigger=<at> rounds=<r> ci=<conclusion> replan=<yes|no> red=<reason> override=<flags|none> open_q=<n> outcome=SHIP`.

      Leave ONE blank line after EACH `<summary>` line so GitHub renders the inner markdown
      (tables / ASCII flow / headers); do NOT wrap a table in a code fence. The structured
      sections (2–9) are now the plan's durable home — `feature-research/` is gitignored and
      scratch is deleted at 8g, and the 🛠 How lives in the diff. Write the body to a temp file,
      use `gh pr create --body-file` (cleaner than inline quoting).
      For a multi-repo run, the PRIMARY repo's PR carries the full body plus a `Companion PRs:` list;
      each companion PR gets the same Source + Summary + Plan, plus a `Part of <task-id>` back-link.

   e. Push + open the draft PR(s) — once per repo in `repos:` with a non-empty diff (single-repo
      run = just the current repo). For each such repo, from its worktree (or `gh -R <owner/repo>`):
      - Clean history (own branch only — Override Policy rule 2): squash this run's commits on
        `<branch>` into a SINGLE well-described commit so the PR merges clean for tidy releases
        (e.g. `git reset --soft <branch-base> && git commit -m "<subject>" -F <body-file>`). This
        rewrites ONLY auto's own `anderson/auto/*` branch.
      - Push: `git push --force-with-lease -u origin <branch>` (squash rewrote the branch;
        force-with-lease permitted HERE — and ONLY here, on auto's own `anderson/auto/*` branch —
        NEVER on the default / shared / human branch without explicit consent). CI veto at step 7c
        may have already pushed this branch; this sends the final squashed state. No remote / push
        fails → degrade gracefully: note it, print that repo's PR body as text.
      - Open: `gh pr create --draft --title "<title> [auto-mode]" --body-file <tmp> --label "auto-mode"`
        (+ `--label needs-human` per step 8c). If `gh` unavailable, print the body and note the
        human should open it. Capture each PR URL.
      - After all PRs open, edit the PRIMARY PR's body to fill its `Companion PRs:` list with the
        other URLs, and each companion's `Part of` back-link.

   f. Set state.md `stage: done`.

   g. Clean up workspace: `git worktree remove` each worktree created in step 2d, then
      `rm -rf feature-research/<task-id>/`. PR(s) + git history are the durable record — the
      plan's durable sections are embedded in the PR body (step 8d items 2–9) and the how is in
      the diff, so nothing of value lost on deletion. (On
      any abort path the scratch + worktrees are KEPT for inspection — do not remove on abort.)

9. REPORT — print the structured terminal result.

   a. (BANNER RULE) Print the REPORT banner now.

   b. Print the structured result:
      ```
      ## Auto-mode result
      status:       SHIP
      task_id:      <task-id>
      pr_url:       <url or "see printed PR body above">
      branch:       <branch>
      tier:         <trivial|normal|hard|critical>   panel_model: <sonnet|opus>
      reviewers:    <n>   arbiter: <ship|fix_first|none> (trigger: <split|unanimous-ship|critical|none>)
      override:     <comma-joined relaxations applied (low-confidence,scope,runaway,sensitive-paths), or none>
      rework_rounds: <n>   replan_bounced: <yes|no>
      plan_gate:    <clear | skipped-trivial | rejected>
      diff_panel:   <pass>  (votes: correctness/regressions+security/plan-match)
      ci:           <ci_status> <ci_conclusion>
      red_reason:   <genuine | green>
      criteria_confidence: <high|low>
      criteria_evidence:
        - <criterion 1> → <plan step / test name>
        - <criterion 2> → …
      open_questions: <n>   (from step 4g; 🔴 = needs human, 🟢 = assumed/deduced)
        - 🔴 <open question> — <why it needs business context>
        - 🟢 <answered question> → <answer>
      residual_risks:
        - <low criteria_confidence, CI in-tree fallback, needs-human flags, open questions, or "none">
      metrics: tier=<t> panel_model=<m> reviewers=<n> arbiter=<v> arbiter_trigger=<at> rounds=<r> ci=<conclusion> replan=<yes|no> red=<reason> override=<flags|none> open_q=<n> outcome=SHIP
      ```
      On abort path, print the report.md contents instead, clearly headed:
      ```
      ## Auto-mode result
      status: ABORTED
      reason: <reason>
      report: feature-research/<task-id>/report.md (scratch retained)
      metrics: tier=<t> panel_model=<m> reviewers=<n> arbiter=<v> arbiter_trigger=<at> rounds=<r> ci=<conclusion> replan=<yes|no> red=<reason> override=<flags|none> open_q=<n> outcome=ABORTED:<reason>
      ```
