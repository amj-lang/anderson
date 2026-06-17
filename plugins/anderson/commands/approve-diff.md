---
description: "Approve the diff review and SHIP for real: commit cleanly on a branch, push, open the PR (all guarded), then remove the scratch dir."
argument-hint: <task-slug>
allowed-tools: Bash(git:*), Bash(gh:*), Bash(rm:*), Bash(cat:*), Bash(echo:*)
---
Task slug = "$ARGUMENTS". This is GATE 2 passing — you've read the diff. In state.md
set diff_verdict=ship, stage=done. This command has side effects (commit, push, PR);
it only runs because you invoked it at the gate. Print what it's about to do before
each network step. NEVER force-push; never touch an existing branch destructively.

1. Build the messages FROM the scratch (it's still present — do this before step 5):
   - Read the goal, the verdict from `diff-review.md`, and "Files changed" + the
     blocking count from `audit.md`.
   - Commit subject (≤72 chars): `<goal>  (review: ship · <N> blocking resolved)`
   - PR body (markdown): 2–4 lines on WHAT changed + WHY (from `plan.md`), the review
     verdict + any notable points (`diff-review.md`), the files touched (`audit.md`),
     and test/lint status. Keep it tight. For a multi-line body, write it to a temp
     file and use `gh pr create --body-file` (cleaner than inline quoting).

2. Pick the branch (defensive — anderson runs in any repo):
   - If `git rev-parse --is-inside-work-tree` fails → not a git repo: skip every git/PR
     step, jump to step 5, and just hand me the commit subject + PR body to use by hand.
   - `current=$(git rev-parse --abbrev-ref HEAD)`.
   - default = remote head if present (`git symbolic-ref --short refs/remotes/origin/HEAD`
     with the leading `origin/` stripped); else `main` if it exists, else `master`.
   - If `current` == default (you're on main/master): create + switch to a slug branch:
     `git switch -c "anderson/$ARGUMENTS"` — but if that branch already exists,
     `git switch "anderson/$ARGUMENTS"` instead (don't clobber). Tell me the branch name.
   - Else (already on a feature branch): commit on the current branch, as-is.

3. Commit cleanly (your git identity — no Claude co-author trailer in your repo):
   - `git add -A` (the scratch dir is gitignored, so only real code is staged).
   - If nothing is staged (`git diff --cached --quiet` succeeds): skip the commit, note
     "nothing to commit (already committed?)", and continue.
   - Else: `git commit -m "<subject>" -m "<PR body>"`.

4. Push + open the PR (guarded — degrade gracefully, never fail the ship):
   - Need a remote (`git remote` is non-empty) AND gh ready (`gh auth status` succeeds).
   - Both present: `git push -u origin "<branch>"`, then
     `gh pr create --base "<default>" --head "<branch>" --title "<subject>" --body-file <tmp>`.
     Capture + print the PR URL.
   - Remote but no gh / not authed: push only, then print the PR body + a compare-URL
     hint so I can open the PR myself.
   - No remote at all: skip the network; the local commit stands. Print the PR body.

5. Remove the disposable scratch: `rm -rf "feature-research/$ARGUMENTS"`.
   (Git history + the PR are the durable record; plan/audit/review were only scaffolding.)

6. (BANNER RULE) Print this SHIP banner (pick ONE ending at random from the 10 — never default to the
   first, and don't reuse one you showed earlier this session) as the LAST framed line before the done line:
   ```
     ╭─ ⌐■-■  SHIP ✓ · THE ONE · welcome to the real world
     │  "[one ending from the pool]"
     ╰─
   ```
   Pool (10 endings): "Green is not understood; read what you merged." / "The gate is not an obstacle; it is the point." / "Review is how respect for the future is spelled." / "You can hand someone the key, but the lock is theirs to turn." / "Ship it, then watch it — shipping is the start of knowing." / "The work is done when the next person needs no story to follow it." / "Every merge is a promise the next outage will test." / "Walk away clean: no scratch, no secrets, no surprises." / "What you shipped is now the truth; make sure it tells no lies." / "The loop ends where your judgement begins."
   Then the done line, filled in with what actually happened (branch + PR URL, or the
   fallback): `✓ [anderson · DONE] $ARGUMENTS shipped on <branch> · <PR url | committed locally, PR body above> · scratch cleaned · loop stopped — nothing runs in the background; /anderson:start to begin again.`
