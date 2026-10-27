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
   - Task key = last `/`-segment of "$ARGUMENTS" (a pasted branch name resolves to the flat
     `feature-research/<key>/`; use the key wherever `$ARGUMENTS` names that dir below).
     Branch name = state.md `branch:` if present (the slug as given at start, e.g. a Linear
     branch `user/ar-123-title`, or the slices file's shared branch), else `anderson/<key>`.
   - If `current` == default (on main/master): create + switch to that branch:
     `git switch -c "<branch>"` — but if it already exists, `git switch "<branch>"` instead
     (don't clobber). Tell me the branch name.
   - Else (already on a feature branch): commit on current branch, as-is.

3. Commit cleanly (your git identity — no Claude co-author trailer in your repo):
   - Stage ONLY the files the run touched: the union of audit.md "Files changed" and repair.md
     "Outside the plan's files" (when it exists), `git add -- <each path>`. Never `git add -A`:
     the tree may hold other tasks' edits or an untracked `.env`. Refuse any path that looks like a
     secret (`.env*`, `*.pem`, `*.key`, `id_rsa*`, `*credentials*`) and tell me instead.
   - If nothing staged (`git diff --cached --quiet` succeeds): skip commit, note
     "nothing to commit (already committed?)", continue.
   - Else: `git commit -m "<subject>" -m "<PR body>"`.

4. Push + open PR (guarded — degrade gracefully, never fail the ship):
   - Need a remote (`git remote` non-empty) AND gh ready (`gh auth status` succeeds).
   - Both present: `git push -u origin "<branch>"`, then
     `gh pr create --base "<default>" --head "<branch>" --title "<subject>" --body-file <tmp>`.
     SLICED (state.md has `slices:`): all slices share one branch and ONE PR.
     · slices file `pr: none` (slice 1) → same `gh pr create`, plus `--draft` while any row is
       still `todo`; write the URL to the file's `pr:`. Prefix the body's What & why with
       `✂ <n> slices, one commit each; draft until the last ships.`
     · `pr:` set (slice ≥ 2) → push only, no new PR. Append this slice's body as a
       `## ✂ Slice <k>: <name>` section (its What & why, criteria table, How to test) to the PR
       body: `gh pr view "<pr>" --json body -q .body` > tmp, append, `gh pr edit "<pr>" --body-file <tmp>`.
     · no `todo` row left after this slice → `gh pr ready "<pr>"`.
     If state.md `open_questions:` > 0 (grill left deferred `[open]` rows), add
     `--label needs-human` to steer reviewer to open business calls; if label doesn't
     exist or `gh` rejects it, drop the flag, open PR anyway (never fail the ship).
     Capture + print the PR URL.
   - Remote but no gh / not authed: push only, then print PR body + a compare-URL
     hint so I can open the PR myself.
   - No remote: skip the network; local commit stands. Print the PR body.

5. Post visual proofs as a PR comment (guarded — do ONLY when a PR was opened AND
   `feature-research/<key>/evidence/`*`.png` exist AND `gh` is ready AND the repo is public:
   `gh repo view --json visibility -q .visibility` prints `PUBLIC`; else skip silently, the
   gate-2 text note in the table stands. A "secret" gist is readable by anyone with the URL,
   so screenshots of a private repo never go there):
   - `gh` cannot inline-upload an image, so host the PNGs on a secret gist:
     `gh gist create --secret feature-research/<key>/evidence/*.png` (one gist; capture its id).
   - Build a comment body: per image `### proof: <criterion #/name>` + `![](<raw-url>)`, where
     raw-url = `https://gist.githubusercontent.com/<user>/<gist-id>/raw/<file>`.
   - `gh pr comment "<pr-url>" --body-file <tmp>`, capture + print the comment URL.
   - Any command here fails → drop it, ship still stands (never fail the ship for a screenshot).
   <!-- ponytail: leaves one orphan gist per ship. Add a cleanup/retention step if they pile up. -->

5b. RIPPLE — only when state.md has `slices:` (skip silently otherwise). Cheap and inline, no
   agent: read the slices file's `**Contracts:**`, then plan.md `## ✅ Decisions` for
   `Contract change:` rows and the committed diff (`git show --stat HEAD` + grep it for each
   contract name) for a contract this slice reshaped.
   - None changed → `ripple · slice <k> · contracts unchanged ✓`.
   - Changed → pause and ask:
     ```
     ripple · slice <k> changed <c> contract(s)
       <name>: <old> → <new>
       affects: <slice # name> (criterion <i>) · …       ← only todo slices that depend on it
       → update those slices? (y / edit / n)
     ```
     `y`/`edit` → rewrite the contract line (append `✎ slice <k>`) and the affected slices'
     Criteria in the slices file. `n` → leave the file, note it under the PR's open questions.
   Then set this slice's Status to `shipped`.

6. Log the run, THEN remove disposable scratch (the log reads state.md, so order matters):
   `python3 "${CLAUDE_PLUGIN_ROOT}/bin/runlog.py" "feature-research/<key>" --mode gated --outcome shipped --pr <PR url, or none>`
   (a local file, never sent anywhere), then `rm -rf "feature-research/<key>"` — only when
   `<key>` is non-empty and contains no `/` or `..`; otherwise leave the scratch and say so.
   (Git history + PR are the durable record; the plan's durable sections — what & why, criteria,
   design, scorecard, blast radius, error handling — are embedded in the PR body at step 1,
   e2e output at step 1's item 5, visual proof at step 5, and the 🛠 How lives in the diff, so
   deleting scratch loses nothing.)

7. Print the done line, filled in with what actually happened (branch + PR URL, or
   fallback): `✓ [anderson · DONE] $ARGUMENTS shipped on <branch> · <PR url | committed locally, PR body above> · scratch cleaned · loop stopped — nothing runs in the background; /anderson:start to begin again.`

8. NEXT SLICE — only when step 5b ran. Next = the first `todo` row (slices run in order). None
   left → delete the slices file, comment on the Linear parent (when one) `all <n> slices
   shipped, PR ready: <pr>`, print `slices · all <n> shipped ✓ · PR ready`, stop.
   Else check this session's size: `cat ~/.claude/fleet/${CLAUDE_SESSION_ID}.status.json`
   (written by the statusline; `ctx_tokens`). Under 250k →
   `next: slice <k> <slice name> · go?` and on my "go" invoke the `anderson:start` skill with
   `<branch> <slice name>`. Over 250k, or the file is missing (budget unknown) → hand off:
   `session ctx <N>k > 250k · next in a fresh session:  /anderson:start <branch> <slice name>`.
