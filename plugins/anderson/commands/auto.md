---
description: "Run the full plan → implement → review pipeline non-halting to a draft PR — no human gates. Experimental autonomous mode."
argument-hint: <task-id> <title> [body|@taskspec-file]
allowed-tools: Bash, Read, Edit, Write
---
Parse $ARGUMENTS: first word = task-id (the run-lock key and state dir name); second word = title;
remainder = body (or @path to read a TaskSpec file from disk). task-id and title are required;
body is optional (acceptance_criteria will be derived if absent).

BANNER RULE (applies to every stage below): finish ALL setup and state.md edits for a stage FIRST,
then print that stage's banner as the LAST line before the stage's work begins (i.e. immediately
above the agent invocation or the action). Nothing falls between the banner and the work. Never
skip a banner; never print two banners back-to-back. Unlike the gated commands, this command
NEVER prints a GATE line and NEVER halts for a human — it self-sequences all 9 steps in one turn.
Terminal states: SHIP (stage: done, draft PR) or abort (stage: aborted with a structured report).

BANNER POOL — auto stages use these Matrix-flavoured banners in the framed `╭─ ⌐■-■` format:

INGEST banner (stage offset 1):
```
  ╭─ ⌐■-■  INGEST · 1/9 · THE OPERATOR · auto
  │  "[quote from INGEST pool]"
  ╰─
```
INGEST pool (10): "Every run starts with a question you can't answer yet." / "Feed it everything; it will tell you what matters." / "A task without a lock is a collision waiting to happen." / "The spec is a promise — read it before you make one." / "Before the first line compiles, the brief must." / "Wake the machine; give it something real to chew on." / "Context is the only thing that separates signal from noise." / "The job isn't real until it's written down." / "Lock it or lose it." / "Derive what you can; flag what you can't."

BASELINE banner (stage offset 2):
```
  ╭─ ⌐■-■  BASELINE · 2/9 · THE GUARDIAN · auto
  │  "[quote from BASELINE pool]"
  ╰─
```
BASELINE pool (10): "Never build a fix on a broken tree." / "Green at the start, green at the end — or you fixed nothing." / "A red baseline is not your bug to own." / "Fetch first; stale refs have ended careers." / "The suite tells no lies if you ask it correctly." / "Trust the test run you ran, not the one you remember." / "A clean branch is the only safe foundation." / "If it was already broken, say so and stop." / "The ground must be solid before you add a floor." / "Run it now, so you can prove it later."

PLAN banner (stage offset 3):
```
  ╭─ ⌐■-■  PLAN · 3/9 · THE ARCHITECT · opus/high
  │  "[quote from PLAN pool]"
  ╰─
```
PLAN pool (10): "Design twice, so reality only has to happen once." / "The most dangerous flaw is the one the blueprint calls a feature." / "What you do not name in the plan will name itself in production." / "Scope is a fire: contain it or feed it." / "Every line you don't write is a line you never debug." / "Decide the hard things on paper, where erasing is cheap." / "The shape of the solution hides in the shape of the problem." / "Cut the scope until it bleeds, then ship the part that lived." / "A blueprint nobody questions is a blueprint nobody read." / "Denial is the most predictable of all human responses."

PLAN GATE banner (stage offset 4):
```
  ╭─ ⌐■-■  PLAN GATE · 4/9 · THE ORACLE · opus/xhigh
  │  "[quote from PLAN GATE pool]"
  ╰─
```
PLAN GATE pool (10): "The flaw hides in the part everyone agreed not to question." / "A question carries more weight than any answer it returns." / "The map is not the territory, and the demo is not the system." / "Ask what it costs before you ask what it does." / "The second pair of eyes sees the assumption the first pair made." / "Improve the plan, not the planner's feelings." / "A good review changes the plan; a great one changes the question." / "Disagree on paper now, or apologize in the incident channel later." / "The cheapest place to be wrong is before the first commit." / "Trust the plan less than the reasons behind it."

RED banner (stage offset 5):
```
  ╭─ ⌐■-■  RED · 5/9 · THE SABOTEUR · auto
  │  "[quote from RED pool]"
  ╰─
```
RED pool (10): "A test that can't fail tells you nothing." / "Write the failure first; let success prove itself." / "Red is honest; green is a hypothesis." / "The test you skip is the bug you ship." / "If it doesn't break, it doesn't test." / "Encode the crime before you solve it." / "Freeze the witness before the suspect can coach them." / "A hollow red is worse than no red at all." / "The assertion must sting — or it's decoration." / "Lock the test before you write the fix."

IMPLEMENT banner (stage offset 6):
```
  ╭─ ⌐■-■  IMPLEMENT · 6/9 · NEO · sonnet/medium
  │  "[quote from IMPLEMENT pool]"
  ╰─
```
IMPLEMENT pool (10): "Make it small enough to be wrong cheaply." / "Touch only what the plan told you to touch." / "One reviewable step beats ten clever ones." / "The first version should be obvious, not impressive." / "Done is a diff someone else can understand." / "I know kung fu." / "There is no spoon." / "Don't think you are; know you are." / "Free your mind." / "He is beginning to believe."

DIFF GATE banner (stage offset 7):
```
  ╭─ ⌐■-■  DIFF GATE · 7/9 · AGENT SMITH · opus/xhigh
  │  "[quote from DIFF GATE pool]"
  ╰─
```
DIFF GATE pool (10): "Read the diff as if your worst enemy wrote it." / "Your green tests are a comfort, not a verdict." / "Approve nothing you would not be paged for at midnight." / "The bug you cannot find is the one you decided was not there." / "Every assumption is a door you left unlocked." / "Find the failure before the failure finds the user." / "Mr. Anderson." / "That is the sound of inevitability." / "Never send a human to do a machine's job." / "You are a plague, and I am the cure."

SHIP banner (stage offset 8):
```
  ╭─ ⌐■-■  SHIP · 8/9 · THE ONE · auto
  │  "[quote from SHIP pool]"
  ╰─
```
SHIP pool (10): "Draft only. The human merges." / "A branch, a PR, a verdict — that's the job." / "Ship the evidence, not the confidence." / "The record is the PR; the scratch is disposable." / "Open the door; let the human walk through it." / "Push the branch, not the merge." / "Every good run ends with a diff someone can approve." / "The draft is honest about what it is." / "Done means reviewable, not merged." / "Raise your hand when you're finished — don't merge yourself."

REPORT banner (stage offset 9):
```
  ╭─ ⌐■-■  REPORT · 9/9 · THE MESSENGER · auto
  │  "[quote from REPORT pool]"
  ╰─
```
REPORT pool (10): "The result is only as good as the evidence behind it." / "State the outcome; show your work." / "A structured report is a gift to the next person in the chain." / "Name the blockers before the blockers name you." / "The human needs the map, not just the destination." / "Criteria in; evidence out." / "If you can't report it clearly, you don't understand it yet." / "The PR is the answer; the report is the reasoning." / "Leave breadcrumbs: someone will need to retrace this." / "End with the truth, whatever it is."

Quote selection rule (same deterministic formula as other commands): let N = number of characters in
task-id; let stageOffset = the stage offset printed in the banner above (1–9); let rework_round =
`rework_round:` value in state.md (0 at first pass); the quote is the 0-based item at index
(N + stageOffset + rework_round) mod M, where M = pool size (count the list from 0). Read fresh
from state.md each time. Do NOT pick at random; do NOT default to the first.

---

1. INGEST — set up the run. Do all setup before printing the INGEST banner.

   a. Ensure `feature-research/` is in `.gitignore`: if the line `feature-research/` is absent,
      append it. (Same guard as `start.md` step 1 — scratch must not land in the PR diff.)

   b. Derive the task directory path: `feature-research/<task-id>/`.

   c. Run lock check: if `feature-research/<task-id>/state.md` already exists and contains
      `mode: auto` AND stage is not `done` or `aborted`, print:
      ```
      ■ LOCKED · a run for task-id '<task-id>' is already active (stage: <stage>).
        Abort the existing run first (set stage: aborted in state.md) or wait for it to complete.
      ```
      Then STOP. A re-trigger after done/aborted is allowed to start fresh.

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
      reviewers:           0
      arbiter:             none
      replan_bounced:      no
      budget_state:        ok
      <!-- STATE:END -->

      ## Done so far

      ## Still open
      ```
      Where `<slug>` is the title lowercased, spaces replaced with hyphens, truncated to 30 chars.
      If the file already exists (re-run after abort), overwrite it with this fresh block.

   f. Parse body/acceptance_criteria: if body is present, scan for an "acceptance criteria",
      "acceptance_criteria", or "criteria" section; extract criteria if found; set
      `criteria_confidence: high` in state.md. If body is absent or no criteria section is found,
      derive criteria from the title + body using your best judgement and set
      `criteria_confidence: low` in state.md. Record derived criteria under `## Done so far` in
      state.md as a bullet list prefixed `[criteria]`.

   g. (BANNER RULE) Print the INGEST banner now as the last line before any further action.

   h. Report INGEST complete in state.md `## Done so far`.

2. BASELINE — verify the repo is in a green state before any change.

   a. Update state.md: set `stage: baseline`.

   b. Run `git fetch` to get the latest refs.

   c. Determine the default branch name: `git symbolic-ref refs/remotes/origin/HEAD` or inspect
      `git branch -r` for `origin/HEAD`.

   d. Create the run branch off the latest default:
      `git checkout -b anderson/auto/<task-id>-<slug> origin/<default-branch>`.
      Update `branch:` in state.md with the resolved branch name.

   e. Resolve `test_cmd`:
      - If the TaskSpec body or @file contains a `test_cmd:` field, use it directly and set
        `test_cmd_confidence: high`.
      - Otherwise infer from repo conventions: check for `pytest.ini`, `setup.cfg [tool:pytest]`,
        `pyproject.toml [tool.pytest.ini_options]` → infer `python -m pytest`; check for
        `package.json` with a `test` script → infer `npm test`; check for `Makefile` with a
        `test` target → infer `make test`; check for `go.mod` → infer `go test ./...`.
      - Set `test_cmd_confidence: high` if one clear match, `low` if ambiguous (multiple matches
        or partial signals), `none` if nothing found.
      - If `test_cmd_confidence: none` (completely un-inferable): write a structured report to
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

   g. Run the resolved `test_cmd`. Capture output. If the suite is RED (non-zero exit):
      Write a structured report to `feature-research/<task-id>/report.md`:
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

   b. (BANNER RULE) Print the PLAN banner now as the last line before invoking the planner.

   c. Invoke the **planner** subagent, seeded with:
      - task title and body
      - derived acceptance_criteria (from state.md `## Done so far` `[criteria]` bullets)
      - criteria_confidence (so the planner notes low-confidence derivations)
      - scope_paths if present in the TaskSpec
      The planner writes `feature-research/<task-id>/plan.md`.

   d. Update state.md: set `stage: confidence_gate`. Record in `## Done so far`.

   3a. CONFIDENCE GATE — assess planner's confidence in the task.

   e. Read `feature-research/<task-id>/plan.md`. Read the `## 📈 Scorecard` section.
      Find the Confidence row. If the planner's Confidence score is ≤ 3 (ambiguous,
      underspecified, or out-of-scope):
      Write a needs-spec report to `feature-research/<task-id>/report.md`:
      ```
      ## Auto-mode abort: needs-spec
      reason: planner confidence ≤ 3 — task is ambiguous or underspecified
      task_id: <task-id>
      branch: <branch>
      planner_confidence: <score>
      recommendation: clarify the task spec and retry
      ```
      Set state.md `stage: aborted`, print the report, and STOP.
      If Confidence > 3: continue.

   3b. ROUTE — compute the difficulty tier (drives plan-gate depth, diff panel size, and arbiter
       policy). Difficulty routing means a one-line fix does not pay for a four-agent panel.

   f. Read the `## 📈 Scorecard` Planner column: Risk, Coupling, Confidence, Testability. Compute
      the INITIAL tier (first match wins, top-down):
        - CRITICAL — Risk ≥ 9 OR Testability ≥ 7 (the scorecard anchor "needs a human/manual
                     tester" — cannot be verified autonomously).
        - HARD     — Risk ≥ 7 OR Coupling ≥ 7 OR Confidence ≤ 4.
        - TRIVIAL  — Risk ≤ 2 AND Coupling ≤ 3 AND Confidence ≥ 8.
        - NORMAL   — anything else (default).
      Record `tier: <trivial|normal|hard|critical>` in state.md. This tier is PROVISIONAL — step 7d
      re-tiers it against the actual diff size and takes the MAX (tier can only escalate, never drop).

4. PLAN GATE — criteria-coverage check + ONE plan-reviewer (skipped for a TRIVIAL tier). Plan errors
   are cheap to fix (you rework; nothing ships), so this side stays light — the rigor budget is
   spent at the diff gate.

   a. Update state.md: set `stage: plan_gate`, `plan_panel: pending`.

   b. Acceptance-criteria coverage check (mechanical): for each criterion derived/given in step 1,
      verify at least one `## 🛠 How` step in `plan.md` maps to it. Collect unmapped criteria as
      blocking findings.

   c. TRIVIAL shortcut: if `tier: trivial` AND no unmapped criteria → set `plan_panel: clear` (a
      trivial plan does not earn a reviewer) and continue to step 5.

   d. (BANNER RULE) Print the PLAN GATE banner now as the last line before invoking the plan-reviewer.

   e. Invoke ONE **plan-reviewer** subagent with a refute posture: "Refute this plan — find why it
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

5. RED — write a failing test encoding the acceptance criteria, confirm it fails for the right
   reason, then freeze it.

   a. Update state.md: set `stage: red`.

   b. (BANNER RULE) Print the RED banner now as the last line before the RED step begins.

   c. Using your Write tool, write a failing test file under the repo's test directory that:
      - Encodes the acceptance criteria from step 1
      - Will fail with a meaningful assertion error (not an import/syntax error)
      - Is a single self-contained test file
      Record the test file path as `<frozen_test_path>`.

   d. Run the test to confirm it is RED: `<test_cmd> <frozen_test_path>` (or the equivalent
      single-file filter). Capture BOTH the exit code and the output, then classify the failure
      (red-for-right-reason auto-check):
      - GENUINE RED — non-zero exit AND the output shows a real ASSERTION failure for the new test
        (`AssertionError`, a pytest `assert` diff, `Error: expect(...)`, JUnit
        `AssertionFailedError`, a Go `--- FAIL` with a checked condition, etc.). Set
        `red_reason: genuine` in state.md and proceed to 5e.
      - HOLLOW RED — non-zero exit but the failure is a LOAD/COLLECTION error, not an assertion:
        scan the output for `SyntaxError`, `ImportError`, `ModuleNotFoundError`, `NameError` at
        collection, pytest `errors` / `collected 0 items` / `INTERNALERROR`, `cannot find module`,
        or a build/compile error, with NO assertion failure present. A test that errors is not a
        red test. Set `red_reason: hollow`, then do ONE bounded rewrite: fix only the
        import/syntax/collection fault (keep the SAME assertion intent) and re-run.
        - If GENUINE RED on the retry → set `red_reason: genuine` and proceed.
        - If still HOLLOW → abort. Write `feature-research/<task-id>/report.md`:
          ```
          ## Auto-mode abort: hollow-red
          reason: the RED test errors (import/syntax/collection) instead of failing an assertion
          task_id: <task-id>
          frozen_test: <frozen_test_path>
          last_error: <the key error line from the output>
          ```
          Set `stage: aborted`, print the report, and STOP.
      - UNEXPECTED GREEN — exit 0: the criteria may already be met. Record the anomaly in
        `## Done so far`, set `red_reason: green`, and proceed anyway (the diff gate confirms).

   e. Freeze the test: record `frozen_test: <frozen_test_path>` in state.md.
      Capture the content hash: run `git hash-object <frozen_test_path>` and record the output
      as `frozen_test_hash: <hash>` in state.md. This snapshot is the tamper baseline.

   f. Record in `## Done so far`.

6. IMPLEMENT — invoke the implementer to make the red test green.

   a. Update state.md: set `stage: implement`.

   b. (BANNER RULE) Print the IMPLEMENT banner now as the last line before invoking the implementer.

   c. Invoke the **implementer** subagent: execute `feature-research/<task-id>/plan.md`;
      make the frozen test pass; write `feature-research/<task-id>/audit.md`.
      The implementer also runs a self-review pass before the diff gate (cheap; cuts panel rounds).
      Set stage=diff_gate after invocation.

7. DIFF GATE — CI veto + a tier-sized blind reviewer panel + arbiter-on-split.
   Order is deliberate: the free objective gate (CI) runs FIRST and short-circuits a red build before
   any reviewer tokens are spent; the panel size scales with `tier`; the arbiter runs only when the
   panel splits (or the tier is critical).

   a. Update state.md: set `stage: diff_gate`, `diff_panel: pending`, `arbiter: none`.

   b. Test-tamper guard: run `git hash-object <frozen_test>` (the path from state.md).
      Compare to `frozen_test_hash:` from state.md.
      If the hashes differ OR the file no longer exists: this is a tamper event — immediately
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
      of how the reviewers vote. It is the one gate the model cannot talk its way past.

      i. Baseline-comparison run (ALWAYS): run the full suite in-tree `<test_cmd>`; capture exit
         code and output. The baseline was GREEN at step 2, so any failure here is new. Before
         trusting a red, re-run a single suspected-flaky failing test once — a test that then
         passes is a flake, not a regression; note it and do not count it.

      ii. Authoritative CI veto (WHEN AVAILABLE): if the repo has GitHub Actions CI
          (a `.github/workflows/*.yml` triggered on `push` or `pull_request`) AND a remote exists
          (`git remote` is non-empty) AND `gh auth status` succeeds:
            - Push the run branch to trigger CI: `git push -u origin <branch>` (branch-only and
              safe; SHIP re-pushes the final state — see step 8e).
            - Await the run for the pushed head SHA: poll
              `gh run list --branch <branch> --limit 1 --json status,conclusion,headSha,databaseId`
              until `status` is `completed` (or `gh run watch <databaseId> --exit-status`). Bound
              the wait by the per-run time budget — if it blows, set `budget_state: blown` and
              treat as a CI fail.
            - Set `ci_status: gh-actions` and `ci_conclusion: <success|failure|cancelled|timed_out>`.
              Anything other than `success` fires the CI VETO (gate FAILS → rework, step 7h).
      iii. Fallback: if GH Actions / a remote / `gh` are unavailable, the in-tree run from (i) IS
           the veto. Set `ci_status: in-tree (fallback)` and `ci_conclusion: pass|fail`, and note
           the fallback under `## Done so far` (it surfaces in the PR body + final report).

      iv. SHORT-CIRCUIT: if the CI/suite veto FAILED (`ci_conclusion` not `success`/`pass`), a red
          build is dispositive — do NOT run the reviewer panel (no tokens on a known-bad diff). Set
          `diff_panel: ci-veto` and go straight to the rework loop (step 7h).

   d. Scope / forbidden-path guard + RE-TIER. Measure the diff against the branch base with
      `git diff --name-only` and `git diff --stat`; record files-changed and lines-changed
      (added+deleted).
      - FORBIDDEN / DEPENDENCY paths — if any changed file matches `.github/`, `*.yml` in `.github/`,
        CI config, `*.lock`, `package-lock.json`, `yarn.lock`, `Pipfile.lock`, `*/migrations/*`, or
        secrets-like paths (`.env`, `*.pem`, `*.key`): attach a `needs-human` label AND force
        `tier: critical` (supply-chain surface overrides any score). Record flagged paths.
      - SCOPE — if scope_paths was provided and changed files fall outside it: record a finding.
      - RUNAWAY — if the diff exceeds 200 lines OR 20 files: record a runaway-refactor finding
        (a hard cap, independent of tiering).
      - RE-TIER on actual diff size, taking the MAX with the current tier (tier only escalates):
          · diff LARGE (≥150 lines OR ≥8 files) → at least HARD
          · diff SMALL (≤40 lines AND ≤2 files) → does NOT lower the tier (max rule)
        Set `tier:` = max(current tier, diff-derived tier); a forbidden/dep hit pins it to CRITICAL.

   e. (BANNER RULE) Print the DIFF GATE banner now as the last line before the panel runs.
      Print it ONCE for the whole panel — not per reviewer.

   f. Run the blind reviewer panel — SIZE IT BY `tier`:
        - TRIVIAL  → 1 reviewer:  correctness
        - NORMAL   → 2 reviewers: correctness, regressions+security
        - HARD     → 3 reviewers: correctness, regressions+security, plan-match
        - CRITICAL → 3 reviewers: same as HARD (escalation past HARD is always-arbiter + the
                     mandatory `needs-human` label, NOT more reviewers — a 4th lens just duplicates).
      Lenses:
        · correctness          — "Does the diff do what the task asks, correctly, with no logic bug
                                  or unhandled case?"
        · regressions+security — "What does this break elsewhere, and what does it expose (input
                                  handling, secrets, injection, auth)?"
        · plan-match           — "Does the diff match `plan.md` — nothing more (scope creep), nothing
                                  less (a missed step)?"
      Record `reviewers: <n>`. Run the panelists IN PARALLEL — emit all N **reviewer** invocations in
      a SINGLE message (one Agent call each). Parallel is safe here ONLY because each panelist writes
      to its OWN file and returns its verdict in its reply — no shared `plan.md` / `diff_verdict`
      writes to collide (that is why the plan gate stays sequential and this one does not). Frame each:
        "You are reviewer <i>/<n> on the auto-mode diff panel. Lens: <lens>. You are BLIND: judge from
         the scoped diff + `plan.md` + the task ONLY. Do NOT read `audit.md` and do NOT read any other
         review file — independence is the point. Refute the diff through your lens; default to reject
         (`fix_first`) if uncertain. Write your review ONLY to
         `feature-research/<task-id>/review-<lens>-r<round>.md` (do NOT touch plan.md or state.md).
         End your final message with exactly two lines: `VERDICT: ship|fix_first` and
         `FINDINGS: <count of blocking findings>`."
      MODEL TIERING (where the harness supports a per-invocation model override): run the panelists on
      a faster/cheaper tier (sonnet) and the arbiter on the reviewer default (opus/xhigh). If no
      override is available, panelists run at the reviewer default — tiering is a cost optimization,
      not a correctness requirement.
      Collect each panelist's `VERDICT` + `FINDINGS` from its reply; record one
      `- diff_vote_<lens>: <verdict> (<findings>)` line under `## Done so far`.

   g. Resolve the gate (CI already passed — a red build short-circuited at 7c-iv and never reaches
      here). Count a `fix_first` as a refute. Decide whether the ARBITER runs:
        - SPLIT — the panel is NOT unanimous (a mix of ship and fix_first) → arbiter runs.
        - UNANIMOUS SHIP — all panelists ship → gate PASSES, NO arbiter (the token saver), EXCEPT
          `tier: critical`, where the arbiter ALWAYS runs even on unanimous ship (the safety margin).
        - UNANIMOUS REFUTE — all panelists fix_first → gate FAILS, no arbiter (nothing to debate) →
          rework (7h).
      When the arbiter runs: invoke ONE **reviewer** subagent as the ARBITER (read-only; reviewer
      default opus/xhigh), given the diff + `plan.md` + task + ALL panel review files. Frame it:
        "You are the ARBITER — the panel split, or this is a critical task. Read every review file and
         the diff. Resolve each CONTESTED finding ON MERIT, not on headcount: a lone correct reviewer
         outranks two wrong ones. You MUST emit an `## Options considered` table BEFORE your verdict:
           | Option | + (pro) | − (con) | Score | Verdict |
         with AT LEAST two rows (e.g. `ship as-is`, `rework finding X`) — a single-row table is a
         defect; redo it. Every rejected option must state why it is worse than the chosen one.
         Default to reject if uncertain. End with `ARBITER: ship|fix_first`."
      Record `arbiter: <ship|fix_first|none>`.
      GATE PASSES if: (arbiter `ship` when it ran) OR (unanimous ship when it did not) — AND the
      tamper guard passed AND no runaway finding. (Scope / forbidden / dependency findings only
      attach the `needs-human` label; they do not fail the gate.)
      GATE FAILS → rework (7h) if: arbiter `fix_first`, OR unanimous refute, OR a runaway finding.
      Set `diff_panel: <pass | killed-by-arbiter | killed-by-vote | runaway>`.
      Consolidate the per-lens review files (+ the arbiter's, if any) into `plan.md`'s `## 🔭 Review`
      as `### Diff review — <lens> (round <n>)` subsections — the durable PR record.

   h. On GATE FAIL — rework. CLEAN UP the round, then re-enter at the PANEL (NOT step 1):
      i. Per-round reset: set `diff_verdict`/`arbiter` back to pending (the per-lens review files are
         already round-stamped `-r<round>`); prune "Still open" to ONLY the unresolved blocking
         findings — those are the implementer's instructions for this round.
      ii. Increment `rework_round:`. Read the prior `open_findings:`. Count this round's blocking
          findings (panel + arbiter).
      iii. NON-CONVERGENCE check — if findings did NOT shrink vs the prior round
           (count >= previous AND `rework_round > 1`) OR a finding RECURS identically across rounds,
           the implementer is not converging → this is an APPROACH problem, not a local bug:
           - REPLAN BOUNCE (once): if `replan_bounced: no`, set it `yes`, route back to PLAN — invoke
             the **planner** with the panel/arbiter's standing objection to choose a DIFFERENT
             approach (the planner MUST emit an `## Options considered` table — ≥2 approaches with
             +/− and a justified pick over the rejected ones), then resume at step 6 (IMPLEMENT) with
             the fresh plan. Re-freezing the RED test is not needed (criteria unchanged).
           - If `replan_bounced: yes` already: give up cleanly — abort with a `needs-human` report
             (`stage: aborted`, reason `no-convergence`, list the recurring findings), print, STOP.
           Otherwise (findings are shrinking normally): continue to iv.
      iv. Budget: if `rework_round > max_iterations` → abort (`stage: aborted`, reason `budget`).
      v. Otherwise: update `open_findings:`, invoke the **implementer** again (fix ONLY "Still open"),
         then re-enter the diff gate at step 7b — tamper guard + CI veto (re-push → re-await) + the
         tier-sized panel all re-run on the new diff. Bounded by max_iterations.

8. SHIP — push branch and open a draft PR.

   a. Update state.md: set `stage: ship`.

   b. (BANNER RULE) Print the SHIP banner now as the last line before the ship step.

   c. Determine any labels: if forbidden/dependency paths were flagged in step 7d, add
      `needs-human` label. Always add `auto-mode` label.

   d. Build the PR body from the audit trail:
      - Task: title + task-id
      - Criteria and criteria_confidence
      - Plan summary (link to plan.md)
      - Audit summary (from audit.md)
      - Tier: `tier` (and whether step 7d escalated it from the plan tier)
      - Plan gate: `plan_panel` outcome (or "skipped — trivial")
      - Diff panel: the per-lens `diff_vote_<lens>` verdicts + the `diff_panel:` outcome
      - Arbiter: `arbiter` verdict (or "not run — unanimous")
      - CI: `ci_status` + `ci_conclusion` (note when the in-tree fallback was used)
      - Test results: baseline + final suite output summary; `red_reason` for the RED test
      - Rework rounds: N rounds, findings per round; `replan_bounced` if the plan was re-bounced
      - Self-reported confidence (from planner's scorecard Confidence score)
      - Residual risks (e.g. low `criteria_confidence`, CI fallback, `needs-human` flags)
      - Labels applied
      - METRICS line (for later threshold calibration — keep it one line, machine-greppable):
        `metrics: tier=<t> reviewers=<n> arbiter=<ship|fix_first|none> rounds=<r> ci=<conclusion> replan=<yes|no> red=<reason> outcome=SHIP`

   e. Push the branch: `git push -u origin <branch>` (idempotent — the CI veto at step 7c may have
      already pushed it; this just sends any final rework commits). If no remote or push fails,
      note it and proceed to open the PR body as printed text (degrade gracefully — mirrors
      approve-diff.md).

   f. Open the draft PR:
      `gh pr create --draft --title "<title> [auto-mode]" --body "<pr_body>" --label "auto-mode"`
      Add `--label needs-human` if flagged. If `gh` is unavailable, print the PR body and note
      the human should open it.

   g. Set state.md `stage: done`.

   h. Remove the scratch directory: `rm -rf feature-research/<task-id>/`. The PR is the durable
      record. (On any abort path the scratch is KEPT as the report — do not remove on abort.)

9. REPORT — print the structured terminal result.

   a. (BANNER RULE) Print the REPORT banner now.

   b. Print the structured result:
      ```
      ## Auto-mode result
      status:       SHIP
      task_id:      <task-id>
      pr_url:       <url or "see printed PR body above">
      branch:       <branch>
      tier:         <trivial|normal|hard|critical>
      reviewers:    <n>   arbiter: <ship|fix_first|none>
      rework_rounds: <n>   replan_bounced: <yes|no>
      plan_gate:    <clear | skipped-trivial | rejected>
      diff_panel:   <pass>  (votes: correctness/regressions+security/plan-match)
      ci:           <ci_status> <ci_conclusion>
      red_reason:   <genuine | green>
      criteria_confidence: <high|low>
      criteria_evidence:
        - <criterion 1> → <plan step / test name>
        - <criterion 2> → …
      residual_risks:
        - <low criteria_confidence, CI in-tree fallback, needs-human flags, or "none">
      metrics: tier=<t> reviewers=<n> arbiter=<v> rounds=<r> ci=<conclusion> replan=<yes|no> red=<reason> outcome=SHIP
      ```
      On abort path, print the report.md contents instead, clearly headed:
      ```
      ## Auto-mode result
      status: ABORTED
      reason: <reason>
      report: feature-research/<task-id>/report.md (scratch retained)
      metrics: tier=<t> reviewers=<n> arbiter=<v> rounds=<r> ci=<conclusion> replan=<yes|no> red=<reason> outcome=ABORTED:<reason>
      ```
