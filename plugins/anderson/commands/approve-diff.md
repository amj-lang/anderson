---
description: "Approve the diff review and SHIP for real: commit cleanly on a branch, push, open the PR (all guarded), then remove the scratch dir."
argument-hint: <task-slug>
allowed-tools: Bash(git:*), Bash(gh:*), Bash(rm:*), Bash(cat:*), Bash(echo:*)
---
Task slug = "$ARGUMENTS". GATE 2 passing — you've read the diff. In state.md
set diff_verdict=ship, stage=done. Command has side effects (commit, push, PR);
runs only because you invoked it at the gate. Print intent before each network
step. NEVER force-push; never touch an existing branch destructively.

1. Build messages FROM the scratch (still present — do before step 6):
   - Read from `plan.md`: goal + 🎯 What + 🤔 Why, the `## ✅ Acceptance criteria` table,
     `## 📈 Scorecard`, `## 🗺 Design`, `## 💥 Blast radius`, `## 🧯 Error handling`, and the
     `## 🔭 Review` verdict + criteria count. Read from `audit.md`: "Files changed", blocking
     count, and `## ⚙️ Setup & test` (test command, manual steps, config/env vars).
   - Commit subject (≤72 chars): `<goal>  (review: ship · <N> blocking resolved)`
   - PR body (markdown) — the whole plan MINUS the how: 🛠 How and ✅ Decisions are DELIBERATELY
     excluded (the diff IS the how — don't double it up). An EMPTY section is OMITTED, never
     printed as "none" filler. Normal (open) sections first, the three reference collapses last.
     In this order:
     1. `Source: <source_url>` — only when state.md `source_url:` ≠ none.
     2. `## 🎯 What & why` — 2–4 lines from plan.md 🎯 What + 🤔 Why.
     3. `## ⚠️ Behavior change` — the plan.md ⚠️ Behavior change line(s) verbatim (≤2 lines).
        OMIT when the plan says "none — internal only".
     4. `## 🗺 Design` — the plan.md 🗺 Design body shown normally (lift it OUT of the plan's
        `<details>` collapse). Omit when the design was a single trivial line already implied by What.
     5. `## ✅ Acceptance criteria` — the plan.md table verbatim, Evidence column filled. Scratch
        dies at ship, so rewrite scratch-path evidence for the PR: visual cells →
        `visual: verified at gate 2` (+ the design source link when one exists; the screenshot
        itself rides a proof comment posted in step 5); e2e cells →
        `e2e: verified at gate 2 (ephemeral, deleted at ship)`. Any `promote candidate` e2e →
        one bullet under the table naming the flow worth a permanent test.
        DISPLAY the e2e output inline: for each `evidence/*.e2e.log` present in scratch, append
        below the table a `<details><summary>proof: e2e #<n></summary>` collapse with the log
        fenced (tail ≤ 40 lines). The script is deleted at ship — this log is the PR's ONLY
        record it ever ran, and it never reaches CI.
     6. `## 🧪 How to test` — reviewer-facing, from audit.md `## ⚙️ Setup & test`: the test
        command to run, plus step-by-step for any `manual`-proof criteria. Then a
        `**Config required:**` line — new env vars / flags / dependencies / manual setup
        (env-var labels and so forth) — ONLY when the change introduced one; omit the line when none.
     7. `## 🔴 Open questions` — ONLY when state.md has `[open]` rows (deferred business calls);
        each as `- <question> — <why it needs a human>` (pairs with the `needs-human` label).
     8. `<details><summary>📈 Scorecard</summary>` — the plan.md Scorecard table verbatim
        (Planner + Reviewer columns).
     9. `<details><summary>💥 Blast radius</summary>` — the plan.md 💥 Blast radius table.
     10. `<details><summary>🧯 Error handling</summary>` — the plan.md 🧯 Error handling table.
     One blank line after each `<summary>` so GitHub renders the inner markdown; do NOT wrap a
     table in a code fence. Multi-line body: write to temp file, use `gh pr create --body-file`
     (cleaner than inline quoting).

2. Pick branch (defensive — anderson runs in any repo):
   - If `git rev-parse --is-inside-work-tree` fails → not a git repo: skip every git/PR
     step, jump to step 6, hand me the commit subject + PR body to use by hand.
   - `current=$(git rev-parse --abbrev-ref HEAD)`.
   - default = remote head if present (`git symbolic-ref --short refs/remotes/origin/HEAD`
     with leading `origin/` stripped); else `main` if it exists, else `master`.
   - If `current` == default (on main/master): create + switch to slug branch:
     `git switch -c "anderson/$ARGUMENTS"` — but if that branch already exists,
     `git switch "anderson/$ARGUMENTS"` instead (don't clobber). Tell me the branch name.
   - Else (already on a feature branch): commit on current branch, as-is.

3. Commit cleanly (your git identity — no Claude co-author trailer in your repo):
   - `git add -A` (scratch dir is gitignored, so only real code is staged).
   - If nothing staged (`git diff --cached --quiet` succeeds): skip commit, note
     "nothing to commit (already committed?)", continue.
   - Else: `git commit -m "<subject>" -m "<PR body>"`.

4. Push + open PR (guarded — degrade gracefully, never fail the ship):
   - Need a remote (`git remote` non-empty) AND gh ready (`gh auth status` succeeds).
   - Both present: `git push -u origin "<branch>"`, then
     `gh pr create --base "<default>" --head "<branch>" --title "<subject>" --body-file <tmp>`.
     If state.md `open_questions:` > 0 (grill left deferred `[open]` rows), add
     `--label needs-human` to steer reviewer to open business calls; if label doesn't
     exist or `gh` rejects it, drop the flag, open PR anyway (never fail the ship).
     Capture + print the PR URL.
   - Remote but no gh / not authed: push only, then print PR body + a compare-URL
     hint so I can open the PR myself.
   - No remote: skip the network; local commit stands. Print the PR body.

5. Post visual proofs as a PR comment (guarded — do ONLY when a PR was opened AND
   `feature-research/$ARGUMENTS/evidence/`*`.png` exist AND `gh` is ready; else skip silently,
   the gate-2 text note in the table stands):
   - `gh` cannot inline-upload an image, so host the PNGs on a secret gist:
     `gh gist create --secret feature-research/$ARGUMENTS/evidence/*.png` (one gist; capture its id).
   - Build a comment body: per image `### proof: <criterion #/name>` + `![](<raw-url>)`, where
     raw-url = `https://gist.githubusercontent.com/<user>/<gist-id>/raw/<file>`.
   - `gh pr comment "<pr-url>" --body-file <tmp>`, capture + print the comment URL.
   - Any command here fails → drop it, ship still stands (never fail the ship for a screenshot).
   <!-- ponytail: leaves one orphan gist per ship. Add a cleanup/retention step if they pile up. -->

6. Remove disposable scratch: `rm -rf "feature-research/$ARGUMENTS"`.
   (Git history + PR are the durable record; the plan's durable sections — what & why, criteria,
   design, scorecard, blast radius, error handling — are embedded in the PR body at step 1,
   e2e output at step 1's item 5, visual proof at step 5, and the 🛠 How lives in the diff, so
   deleting scratch loses nothing.)

7. (BANNER RULE) Print this SHIP banner (choose ending by COUNTING, not feel: N = task slug character count (every character, hyphens included); iteration = `iteration:` value in state.md (read fresh); ending = 0-based item at index (N + 6 + iteration) mod M; M = integer in "Pool (M endings):" label below; count list from 0; mod M always yields valid position (0 to M−1); label number must equal actual ending count. Do NOT pick "at random", do NOT default to first.) as the LAST framed line before the done line:
   ```
     ╭─ ⌐■-■  SHIP ✓ · THE ONE · welcome to the real world
     │  "[one ending from the pool]"
     ╰─
   ```
   Pool (24 endings): "Green is not understood; read what you merged." / "The gate is not an obstacle; it is the point." / "Review is how respect for the future is spelled." / "You can hand someone the key, but the lock is theirs to turn." / "Ship it, then watch it — shipping is the start of knowing." / "The work is done when the next person needs no story to follow it." / "Every merge is a promise the next outage will test." / "Walk away clean: no scratch, no secrets, no surprises." / "What you shipped is now the truth; make sure it tells no lies." / "The loop ends where your judgement begins." / "Because I choose to." / "Where we go from there is a choice I leave to you." / "I know you're out there; I can feel you now." / "A world where anything is possible." / "Everything that has a beginning has an end." / "There's no escaping reason, no denying purpose." / "I'm going to show them a world without rules and controls." / "The body cannot live without the mind." / "Some things change; some things never do." / "Free minds." / "One clean commit; one honest history." / "Read what you shipped before the user does." / "Clean branch, clean history, clean conscience." / "The key is yours now; turn it knowingly."
   Then the done line, filled in with what actually happened (branch + PR URL, or
   fallback): `✓ [anderson · DONE] $ARGUMENTS shipped on <branch> · <PR url | committed locally, PR body above> · scratch cleaned · loop stopped — nothing runs in the background; /anderson:start to begin again.`
