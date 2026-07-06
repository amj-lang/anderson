---
description: "Approve the diff review and SHIP for real: commit cleanly on a branch, push, open the PR (all guarded), then remove the scratch dir."
argument-hint: <task-slug>
allowed-tools: Bash(git:*), Bash(gh:*), Bash(rm:*), Bash(cat:*), Bash(echo:*)
---
Task slug = "$ARGUMENTS". GATE 2 passing — you've read the diff. In state.md
set diff_verdict=ship, stage=done. Command has side effects (commit, push, PR);
runs only because you invoked it at the gate. Print intent before each network
step. NEVER force-push; never touch an existing branch destructively.

1. Build messages FROM the scratch (still present — do before step 5):
   - Read goal, verdict from `plan.md` `## 🔭 Review`, and "Files changed" + blocking
     count from `audit.md`.
   - Commit subject (≤72 chars): `<goal>  (review: ship · <N> blocking resolved)`
   - PR body (markdown), VISIBLE essentials first, each tight: 2–4 lines WHAT changed + WHY
     (from `plan.md`); `## 🧪 How to test` block (test command + covering test,
     from `audit.md` `## ⚙️ Setup & test`); `## ⚙️ Setup & requirements` block (new env vars /
     dependencies / config, or "none" — also from `audit.md` `## ⚙️ Setup & test`);
     `## ❓ Open questions & assumptions` block from state.md `## ❓ Open questions` (what grill
     resolved or deferred — PR reviewer sees it without unfolding plan), two terse lists,
     omit empty list; both empty → one line "None — all error paths resolved in the
     grill": **🔴 Open (deferred — needs a human):** each `[open]` line as `- <question> — <why>`;
     **🟢 Resolved / assumed:** each `[answered]` line as `- <question> → <answer>`. Review
     verdict + notable points (`plan.md` `## 🔭 Review`); files touched (`audit.md`);
     test/lint status. Then append a `<details><summary>📋 Full plan (as
     reviewed)</summary>` collapse embedding the ENTIRE `plan.md` verbatim (🗺 Design, 💥 Blast
     radius, 🧯 Error handling, 📈 Scorecard, ✅ Decisions, `## 🔭 Review`) — `feature-research/`
     is gitignored and step 5 deletes scratch, so this collapse is the plan's only durable
     GitHub home. One blank line after `<summary>` so GitHub renders inner markdown; do
     NOT wrap plan in a code fence (it has its own). Multi-line body: write to temp file,
     use `gh pr create --body-file` (cleaner than inline quoting).

2. Pick branch (defensive — anderson runs in any repo):
   - If `git rev-parse --is-inside-work-tree` fails → not a git repo: skip every git/PR
     step, jump to step 5, hand me the commit subject + PR body to use by hand.
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

5. Remove disposable scratch: `rm -rf "feature-research/$ARGUMENTS"`.
   (Git history + PR are the durable record; full plan embedded in PR body at
   step 1 — deleting scratch loses nothing.)

6. (BANNER RULE) Print this SHIP banner (choose ending by COUNTING, not feel: N = task slug character count (every character, hyphens included); iteration = `iteration:` value in state.md (read fresh); ending = 0-based item at index (N + 6 + iteration) mod M; M = integer in "Pool (M endings):" label below; count list from 0; mod M always yields valid position (0 to M−1); label number must equal actual ending count. Do NOT pick "at random", do NOT default to first.) as the LAST framed line before the done line:
   ```
     ╭─ ⌐■-■  SHIP ✓ · THE ONE · welcome to the real world
     │  "[one ending from the pool]"
     ╰─
   ```
   Pool (24 endings): "Green is not understood; read what you merged." / "The gate is not an obstacle; it is the point." / "Review is how respect for the future is spelled." / "You can hand someone the key, but the lock is theirs to turn." / "Ship it, then watch it — shipping is the start of knowing." / "The work is done when the next person needs no story to follow it." / "Every merge is a promise the next outage will test." / "Walk away clean: no scratch, no secrets, no surprises." / "What you shipped is now the truth; make sure it tells no lies." / "The loop ends where your judgement begins." / "Because I choose to." / "Where we go from there is a choice I leave to you." / "I know you're out there; I can feel you now." / "A world where anything is possible." / "Everything that has a beginning has an end." / "There's no escaping reason, no denying purpose." / "I'm going to show them a world without rules and controls." / "The body cannot live without the mind." / "Some things change; some things never do." / "Free minds." / "One clean commit; one honest history." / "Read what you shipped before the user does." / "Clean branch, clean history, clean conscience." / "The key is yours now; turn it knowingly."
   Then the done line, filled in with what actually happened (branch + PR URL, or
   fallback): `✓ [anderson · DONE] $ARGUMENTS shipped on <branch> · <PR url | committed locally, PR body above> · scratch cleaned · loop stopped — nothing runs in the background; /anderson:start to begin again.`
