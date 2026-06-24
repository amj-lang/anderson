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

4. PLAN GATE (stub) — single-critic plan review + criteria-coverage check.

   a. Update state.md: set `stage: plan_gate`.

   b. Acceptance-criteria coverage check: for each criterion derived/given in step 1, verify
      that at least one `## 🛠 How` step in `plan.md` can be mapped to that criterion.
      Unmapped criteria are blocking findings — collect them.

   c. (BANNER RULE) Print the PLAN GATE banner now as the last line before invoking the plan-reviewer.

   d. Invoke the **plan-reviewer** subagent with a refute-lens prompt: "Refute this plan. Find
      why it fails or misses an acceptance criterion. Default to reject if uncertain."
      The plan-reviewer edits `plan.md` inline and appends its review to `## 🔭 Review`;
      sets `plan_verdict` in state.md.
      # TODO(panel): replace with 3-lens critic panel (feasibility/coverage/blast-radius),
      # majority-refute threshold. This increment: single reviewer, refute posture.

   e. Read `plan_verdict` from state.md after the plan-reviewer runs.
      - If `plan_verdict: ship` AND no unmapped criteria: continue to step 5.
      - If `plan_verdict: fix_first` OR unmapped criteria exist: this is fixable — do one
        bounded plan-rework pass: invoke the **planner** again with the specific blockers,
        then re-run the plan-reviewer (steps d–e above, once only). If still not `ship`, abort:
        write a report (`stage: aborted`, reason `plan-rejected`), print it, and STOP.
      - If `plan_verdict: regrill` or hard-reject language in the review: abort immediately.
        Write report (`stage: aborted`, reason `plan-rejected`), print it, and STOP.

5. RED (stub) — write a failing test encoding the acceptance criteria, then freeze it.

   a. Update state.md: set `stage: red`.

   b. (BANNER RULE) Print the RED banner now as the last line before the RED step begins.

   c. Using your Write tool, write a failing test file under the repo's test directory that:
      - Encodes the acceptance criteria from step 1
      - Will fail with a meaningful assertion error (not an import/syntax error)
      - Is a single self-contained test file
      Record the test file path as `<frozen_test_path>`.
      # TODO(red): red-for-right-reason auto-check — in v1 the model judges whether the
      # failure is a genuine assertion vs an import/syntax error. Add automated detection
      # (parse stderr for SyntaxError/ImportError) next increment.

   d. Run the test to confirm it is RED:
      `<test_cmd> <frozen_test_path>` (or equivalent filter). If it exits 0 (unexpected green),
      the criteria may already be met — record this anomaly in `## Done so far` and proceed
      anyway (the diff gate will confirm).

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

7. DIFF GATE (stub) + CI veto (stub) — blind review, tamper guard, scope check, suite.

   a. Update state.md: set `stage: diff_gate`.

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

   c. Run the full test suite: `<test_cmd>`. Capture exit code and output.
      # TODO(ci): replace with real CI runner (GH Actions) — see open question 1 in docs/auto-mode.md.
      # This increment: run the suite in-tree on the current branch.

   d. Scope and forbidden-path guard: run `git diff --name-only HEAD~1` (or against the branch
      base). Check each changed file:
      - If any file matches `.github/`, `*.yml` in `.github/`, CI config paths, `*.lock`,
        `package-lock.json`, `yarn.lock`, `Pipfile.lock`, migration files (`*/migrations/*`),
        or secrets-like paths (`.env`, `*.pem`, `*.key`): set a `needs-human` label for the PR.
        Record flagged paths in state.md `## Done so far`.
      - If scope_paths was provided and changed files fall outside it: record as a finding.
      - If diff exceeds 200 lines or 20 files: record as a runaway-refactor finding.

   e. (BANNER RULE) Print the DIFF GATE banner now as the last line before invoking the reviewer.

   f. Invoke the **reviewer** subagent — blind context: provide diff + plan + task only (NOT the
      implementer's self-justification). The reviewer appends its review to `## 🔭 Review` in
      `plan.md` and sets `diff_verdict` in state.md.
      # TODO(panel): replace with 3 blind reviewers (correctness / plan-match / regressions+security),
      # kill if ≥2/3 refute. This increment: single reviewer, refute posture.

   g. Read `diff_verdict` from state.md. Evaluate gate:
      - GATE PASSES if: `diff_verdict: ship` AND suite is GREEN AND tamper guard passed AND no
        runaway-refactor finding (or scope/forbidden findings only warrant `needs-human` label,
        not an abort).
      - GATE FAILS if: `diff_verdict: fix_first` OR suite is RED OR tamper guard triggered OR
        runaway-refactor abort.

   h. On GATE FAIL — rework loop:
      Read `rework_round:` from state.md. Increment it by 1.
      Read `open_findings:` (the count from the previous round, or 0 on first fail).
      Count new findings from the reviewer's output. If finding count >= previous `open_findings`
      AND `rework_round: > 1` (i.e. findings did not shrink across two rounds):
        Thrash breaker fires — abort:
        ```
        ## Auto-mode abort: thrash
        reason: open findings did not shrink across two rework rounds
        task_id: <task-id>
        rework_round: <n>
        open_findings: <count>
        ```
        Set `stage: aborted`, print report, STOP.
      Update `open_findings:` and `rework_round:` in state.md.
      If `rework_round > max_iterations`: abort with budget report (stage: aborted, reason: budget).
      Otherwise: invoke the **implementer** again (fix only "Still open" from state.md), then
      re-run the diff gate checks from step 7b. Loop is bounded by max_iterations.

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
      - Test results: baseline + final suite output summary
      - Rework rounds: N rounds, findings per round
      - Self-reported confidence (from planner's scorecard Confidence score)
      - Residual risks and stubs (TODO items from this run)
      - Labels applied

   e. Push the branch: `git push -u origin <branch>`. If no remote or push fails, note it and
      proceed to open the PR body as printed text (degrade gracefully — mirrors approve-diff.md).

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
      rework_rounds: <n>
      criteria_confidence: <high|low>
      criteria_evidence:
        - <criterion 1> → <plan step / test name>
        - <criterion 2> → …
      residual_risks:
        - <any TODO(panel)/TODO(ci)/TODO(red) stubs active this run>
      ```
      On abort path, print the report.md contents instead, clearly headed:
      ```
      ## Auto-mode result
      status: ABORTED
      reason: <reason>
      report: feature-research/<task-id>/report.md (scratch retained)
      ```
