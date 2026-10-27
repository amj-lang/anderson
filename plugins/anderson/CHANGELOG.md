# anderson changelog


- **0.73.0** — **Slices stack on one PR; slice only past 250k; the run log measures it.** A split task no longer makes one Linear sub-issue, branch and PR per slice: slices run in order on one branch, slice 1 opens a draft PR, each later slice adds a commit and a `## ✂ Slice <k>` section, the last marks it ready. One comment on the Linear parent replaces the sub-issues. `/anderson:start <branch>` picks up the next `todo` slice and switches to the shared branch first. The planner slices at ~250k (was 150k) and drops the 7-criteria trigger: each slice costs a re-plan and review, so only big jobs pay. Diff reviewers log `diff_blocking: <n>` per round; `runlog.py` records it with the planner's `size_k`, and `--summary` prints first-review blocking by implement-token bucket so the line can move on evidence. Fleet reads the new 5-column slices table.
- **0.72.1** — **The scheduler no longer moves plan → grill before plan.md exists.** A Stop fires when the main turn ends, which happens while the planner still runs in the background; the hook advanced the stage anyway, so the band showed "grill" over a live THE ARCHITECT and the human was told to grill a plan that was not written. Also: `/anderson:start`'s seed line passes `$ARGUMENTS` (the first word is the slug) instead of `$1 $2`, which expanded to the wrong words. And a live crew seat without a sprite (SERAPH, NIOBE, THE MEROVINGIAN) showed the stage's face; it now shows none.
- **0.72.0** — **Tier recalibration + per-tier cost in the run log.** 25 of 31 tiered runs landed HARD or CRITICAL, so nearly every diff review ran opus/xhigh. New rules, identical in tiering.md, start.md, auto.md, approve-plan.md and rework.md (a drift test pins them): CRITICAL is `Risk ≥ 9` only; HARD is `Risk ≥ 7` OR `Coupling ≥ 8` OR `Confidence ≤ 3` OR `Testability ≥ 7` OR a change that *alters* an auth/permission check, secret/crypto handling, locking/concurrency or builds a shell command / path from external input OR adds/changes an externally reachable entry point; the diff re-tier is ≥400 changed lines or ≥15 files (tests, lockfiles, generated files excluded). Tier still only escalates. Auto keeps the `needs-human` label for `Testability ≥ 7` now that it no longer means CRITICAL. The planner's Risk and Coupling anchors gain mid-scale examples. Band: each finished subagent seat appends `{stage, seat, model, tokens, start, end}` to `feature-research/<task>/cost.jsonl` (only while the task's scratch dir exists; `.`/`..` slugs are never pinned). `runlog.py` folds the ledger into each run line (`cost`, `tokens`, `duration_ms`), adds the planner `scorecard` and `tier_line`, then removes the ledger so a re-run slug never double-counts; `--summary` prints median tokens, median time and rework rate per tier (`n/a` for older runs).
- **0.71.0** — **Crew audit: the band tracks the session's own task, fleet idles cheap, ship stages only what the audit lists.** SERAPH, NIOBE and THE MEROVINGIAN sat over the whole plugin. Band: a hand-written crew brief ("You are seated as SERAPH, the security lens of …") now lands the right seat instead of three AGENT SMITHs; the band pins the task from this session's own prompts (`/anderson:<cmd> <slug>` or a `feature-research/<task>/` path) instead of the newest state.md in the repo, and re-reads state.md every 2 s so a stage written by a tool shows without waiting for the next event; one timer, no stacking on resume. Fleet: usage limits computed once per scan, dead sessions dropped before their transcript is parsed, `~/.claude/fleet` rotated (stale+dead sessions and week-old files removed), cwd cached per pid, one stat pass per subagent; discover 184→28 ms, render 20→2 ms. Hooks: the per-tool-call pid walk is skipped while the recorded pid is alive (30→18 ms). Security: the scheduler ignores a state.md whose `task:` is not a plain slug (a crafted name rode into the hook's block reason); approve-diff and feature.sh stage only the audit's files, never `git add -A`, and refuse secret-looking paths; evidence gists only on public repos (a secret gist is readable by URL); ticket, TaskSpec and design text reach the agents as an `<untrusted-ticket>` block, instructions inside it abort to a human; CI token is read-only except for the release job. Scheduler no longer chains implement/repair → diff_review (approve-plan self-sequences those; the directive raced it mid-repair). Docs: changelog moved here; banner prose → band; `bin/banner.sh`, `bin/matrix.sh` and `docs/auto-mode-handoff.md` deleted; demo's TRINITY is opus/high; a missing tier reports as normal. Shellcheck is blocking.
- **0.70.0** — **Animated persona portraits in the band.** NES-style 24×24 pixel portraits (`hooks/band/portraits.ts`) sit at the band's right edge, 8 cols × 4 rows, drawn as real pixels where the terminal can (Ghostty, kitty) and the persona's name elsewhere. Who shows: the newest live seat with a portrait, else the stage's persona. Each moves on the band's 250 ms tick over Matrix rain: NEO's shades glint, SMITH's earpiece blinks and he glitches into a copy, TRINITY looks around, THE ORACLE smokes, THE ARCHITECT has code in his glasses. Hidden under 80 columns.
- **0.69.0** — **Band replaces the stage banners.** The `╭─ ⌐■-■ STAGE · n/5 · PERSONA` banners and their quote pools are gone from every command (start, approve-plan, rework, approve-diff, auto, proto): the band above the prompt already shows stage, persona and model live. Gate cards keep every line, minus the art (`🔴 GATE 1 · YOUR TURN`). `/anderson:demo` now previews the band; `bin/demo.sh` removed. Band boxes back to a fixed 34 columns; the header rule still spans the terminal.
- **0.68.2** — Band box: gap between a long model name (`sonnet/medium`) and the timer.
- **0.68.1** — Band no longer repeats `your turn ▸ answer the grill`: the grill's own card already asks.
- **0.68.0** — **Band spans the terminal; tokens instead of `$`.** The band header ends in a rule to the terminal's full width and crew boxes stretch to fill each row. The header shows this session's tokens, `I: 1.2M / O: 35k` (main loop and subagents; input counts cache reads/writes), in place of the dollar figure.
- **0.67.0** — **Crew band above the prompt.** A Claude Code mod (function hooks, `hooks/band/`) draws the live crew just above the input: one box per running subagent with persona, model/effort (read from the agent's frontmatter), elapsed time, and what it is doing right now (its last tool call). A finished seat shows its verdict (`✓ 0 blocking · 1 nit`, `✗ 1 blocking` in red) and stays on screen through the gate; a seat with no tool call for 2 minutes turns yellow as stalled. The header carries stage dots (`●●●●●◐○`), the stage, and at a gate the exact command to type next. When the crew is too wide, finished seats shrink to one-line cells. Needs a Claude Code build with mods (function hooks); the statusline and fleet are unchanged. Persona names stay in step with the statusline (`test/test_band_personas.py`).
- **0.66.0** — **Prototypes: pick by looking.** New `/anderson:proto <what>` and the `prototyper` agent (THE CONSTRUCT, sonnet/medium): 2-3 throwaway variants that differ on a core axis (layout, hierarchy, interaction), never three shades of one idea. Terminal targets get ASCII at the real width, through the repo's own renderer when it has one; web targets get self-contained HTML using the repo's design tokens, opened in the browser. Pick a letter, ask for a mix, or `again <steer>`. Inside a task the pick is copied into `design/`, its exact strings go to `inventory.md`, and the grill folds it in as a `source: design` criterion, so the diff review checks the build against what you picked. The grill flags 🎨 visual questions and offers the prototype instead of asking in words. Never runs in auto mode. Storybook as a UI-first slice comes later.

- **0.65.2** — **Docs catch up with slicing.** The root README explains big-task slicing and the fleet `✂` tag; the plugin README's Pipeline section documents the Size line, the split, slice mode and the ripple check; the plugin and marketplace descriptions mention it.
- **0.65.1** — **Fleet reads only real slices files.** `slices:` in state.md must name a regular `*.slices.md` directly in the repo's `feature-research` dir; an absolute path, `..`, a device or a FIFO is ignored, and the read is capped. Before, a crafted state.md could make fleet read any file or hang on `/dev/zero`.
- **0.65.0** — **Fleet shows slices.** A row whose task is a slice of a split task gets `✂ 2/3` after the task name (`s 2/3` with `--ascii`), from state.md `slice:`. The selected row's card adds a `slice` line: the parent ticket, each contract (✓ unchanged, ✎ changed by a ripple) and the next slice with what it still waits on, read from the slices file. Unsliced tasks look exactly as before.
- **0.64.0** — **Token slicing.** The planner now estimates how many tokens the implement stage needs and divides by 150k, the rough edge of the smart zone. One slice: nothing changes. Two or more: it plans slice 1, lists the rest with the contracts between them (the black boxes a later slice builds on), and Gate 1 asks once whether to split. `y` creates Linear sub-issues under the ticket (`blockedBy` wired, one comment on the parent, its description never touched) or local slices without Linear, then approves slice 1. Credit: the slicing rule (tokens ÷ 150k, one fresh session per ticket) and the grill both come from [Matt Pocock](https://github.com/mattpocock/skills); "smart zone" is Dex Horthy's term. Each later slice started from its sub-issue only grills what the parent grill didn't settle. After each ship, a ripple check compares the slice against the contracts: unchanged is one line, a change pauses and asks before updating the downstream slices. Then it offers the next unblocked slice, in this session while it stays under 150k, else as a command for a fresh one. `/anderson:auto` is unchanged.

- **0.63.0** — **Fleet, focused on following your agents.** Each row shows Claude's own title for the session (the one on its tab) instead of a cut-off first prompt. Persona, stage, tier and model merge into one `pipeline` cell, blank for sessions without anderson, so the `now` column (what it is doing) gets the room. Sessions you closed, and ones dead for over an hour, fold into one `dead (n)` line. After `N`, the new agent is selected as soon as it appears, so `⏎` follows it. Cut: the four extra themes (matrix stays; `--calm` is the motion switch), `--theme`, `--demo`, `--rings`, `--play`, `--ping`. The README says what anderson and fleet do in plainer words.
- **0.62.0** — **Fleet, cleaned up: fewer keys, rings that mean it, ⏎ that lands.** Rings: the row no longer rings on every mid-turn line of text (the transcript guess overrode the hooks whenever the model wrote "Now let me check X" between tools); hooks are the truth now, a ring alerts once after 5 s so a Stop the scheduler blocks never rings, a `PreToolUse` hook clears it the moment the session moves on, `AskUserQuestion` / `ExitPlanMode` ring as questions, and the wait time survives the idle notification. A Ghostty session no longer counts as watched just because some Ghostty window is in front. `m` mutes every running fleet at once, and banners stop playing their own sound. Jack in asks only the app that owns the session (Terminal.app and iTerm2 no longer flash forward to be searched), finds Ghostty tabs by the directory claude started in when the tty mark misses, caches the tab per session, and a tmux session with no attached client opens in a new tab instead of taking over fleet's. Clicking a ring banner jumps to that session (`--jack`), `fleet --focus` brings fleet back. Layout: live sessions on top, the workspace's repos below for `N`; the repo/group tree, drill-in, auto-zoom and reorder are gone. Keys cut: `J`/`K`, `→`/`←`, `D` pop out, `O` open in IDE (and the auto-open on ⏎), `a` agent log, `c` copy resume, `R` rebase + force-push, `n` / `s` / `$` / `t` / `p` / `+` / `-` (the settings stay as flags; zoom is gone). `fleet` runs in place by default instead of wrapping itself in tmux. `--ascii` now actually switches the footer and markers to ASCII.
- **0.61.0** — **Fleet: one row per session, worktrees under their repo, ⏎ past a stray Ghostty, shipped in red.** Sessions sharing a checkout no longer wear each other's task: a hooked session that touched no task shows its own prompt instead of borrowing the newest state.md (why three unrelated agents all read `ar-1432 · INTERROGATOR · grill`). A session in any linked worktree (`.claude/worktrees/`, `.worktrees/`, a sibling dir) rows under its main checkout, read off the worktree's `.git` file, instead of landing in `elsewhere`; sibling worktrees stop showing as idle repo rows. The branch is read live from the checkout's HEAD, so a session that moved into a worktree shows that worktree's branch, not the one its transcript started on. ⏎ into Ghostty talks to the instance that owns the session (JXA by pid): a second Ghostty an agent started with `ghostty -e` used to answer AppleScript and hide every real tab. A shipped (`done`) row renders red.
- **0.60.0** — **The crew sits at plan review too.** SERAPH and NIOBE now judge the design before THE ORACLE, not only the finished code: a missing authorization check, unvalidated input, an N+1 query or an unbounded fetch is one plan edit at plan review and a full rework round at diff review. `bin/crew.py --plan plan.md` routes from the plan's Files touched and text (no diff exists yet); THE ORACLE reads the seats' `plan-review-<lens>.md` files, confirms or rejects each finding on merit, folds the confirmed ones into plan.md and logs `plan_tally:`, which `bin/runlog.py --summary` reports per seat. THE MEROVINGIAN stays diff-only: orphaned code needs a diff, and the blast-radius check already covers planned dead code. The diff crew is unchanged, so it verifies the code against a plan that was already security- and performance-reviewed.
- **0.59.1** — **Fleet: ⏎ finds the right Ghostty tab when several agents share a repo.** Ghostty's AppleScript has no tty, so jack in matched tabs by working directory and gave up with "N tabs in <repo>, can't tell which" once two claude sessions ran in one checkout. It now writes a one-off title to the session's own tty, focuses the tab showing it, and puts the old title back: exact for any number of tabs. The directory match stays as the fallback.
- **0.59.0** — **Gate 2 shows the code diff.** The card said "read the diff" but nothing showed it: fleet's `o` only paged plan.md + audit.md. At diff review `o` now pages the code diff after them (tracked changes vs HEAD plus new files, scratch left out, read-only), and the Gate 2 card names the in-session commands (`! git diff HEAD`, `! git status -s`). The PR body is unchanged: still the plan minus the how, no diff in it.
- **0.58.0** — **Fleet: ⏎ lands on Ghostty tabs, `N` spawns.** Jack in never found a session running in Ghostty: its AppleScript dictionary has no tty, so fleet fell back to "app focused, tab not selectable". It now finds the tab by working directory (a claude title beats a bare shell sharing the directory) and focuses it; spawned Ghostty tabs start in their repo so they are found from the first frame. `⏎` only moves you now: on a repo/group row it goes in, like `→`, instead of opening the spawn prompt. Spawning moved to `N` (new agent), which also works on a session row (into its repo) and in an empty repo you drilled into.
- **0.57.1** — **Fleet: spawns open a tab in the terminal you run it in.** `⏎` spawn, sentinel revive and `D` pop-out always went to Terminal.app unless fleet ran in iTerm2, so from Ghostty (and from any terminal once fleet sat inside tmux, where `TERM_PROGRAM` reads `tmux`) the agent landed in the wrong app or failed. fleet now reads the host app from `__CFBundleIdentifier`, which survives tmux, and opens a new **tab** there: Ghostty 1.3+ through its AppleScript dictionary, iTerm2 in its current window. Terminal.app keeps its new window (a tab there needs Accessibility keystrokes).
- **0.57.0** — **Crew hint and the run log.** The planner can add a diff-review seat the routing rules would miss (`**Crew hint:**` in plan.md; the plan-reviewer may add to it, never remove), and `bin/crew.py --hint` takes the union: judgment can only add a reviewer, never drop one. Every finished run, shipped or aborted, appends one JSON line to a local run log (`~/.claude/anderson/runs.jsonl`, never sent anywhere) and `bin/runlog.py --summary` reports tiers, rework rounds and each crew seat's confirmed/raised hit rate, the evidence for tuning tiers and crew patterns. Smith's tally line is now `crew_tally:` so it can't collide with the `crew:` state field.

- **0.56.0** — **Sharper crew profiles; context7 reaches the builders.** SERAPH establishes the trust boundary first (from CLAUDE.md / SECURITY.md / README, or names its assumption), runs `npm audit` on dependency changes and `gitleaks` / `semgrep` when installed, and ignores fixture secrets. NIOBE decides hot versus cold paths with LSP `incomingCalls` and sizes new client dependencies. THE MEROVINGIAN greps a symbol's name as a string before calling it dead and treats convention-loaded files (framework routes, configs, stories, workers) as live. Every lens finding carries `severity · confidence`, and AGENT SMITH logs each seat's confirmed/raised tally so its hit rate is measurable. The planner reads `docs/adr/` and `CONTEXT.md`. Planner, plan-reviewer, implementer and test-fixer get the context7 docs tool (installed version's types first).

- **0.55.1** — **NIOBE and THE MEROVINGIAN move off Sonnet.** Performance and dead-code calls are judgment, not pattern matching: both seats now run opus/medium below HARD and opus/high from HARD up (SERAPH stays opus/high). Medium needs its own twin, `reviewer-medium`, since effort is frontmatter-only; `bin/crew.py` now names the agent per seat and the twin test covers all three twins.

- **0.55.0** — **The crew: SERAPH, NIOBE and THE MEROVINGIAN join the diff review; LSP reaches every agent; typecheck and lint are enforced.** Three lens seats of the `reviewer` agent (no new agent files), summoned by `bin/crew.py` from the diff's paths and changed lines: SERAPH (security, always from HARD up), NIOBE (performance), THE MEROVINGIAN (dead code this diff orphaned, traced with LSP `findReferences`). They review blind in parallel into their own files, then AGENT SMITH (gated) or the arbiter (auto) rules on their findings. The planner's blast radius gains a 'code this change makes dead' vector so deletions get planned. Every agent gets the `LSP` tool (exact reference tracing; Grep as fallback). The implementer runs the repo's typecheck and lint before finishing and the reviewer re-runs them: the 'lint clean' exit rule was never enforced. Auto mode: HARD now includes security/auth/concurrency changes (it had drifted from start mode), and the diff guard counts untracked new files.

- **0.54.0** — **Agent audit against Claude's prompt-audit guide; xhigh review seats are real.** Effort is frontmatter-only (the Agent tool has no per-call effort), so the tiered "effort override" never ran: CRITICAL plan review and HARD+ diff review ran at high. New `plan-reviewer-xhigh` / `reviewer-xhigh` twins (same body, `effort: xhigh`, kept identical by `test/test_agent_variants.py`) and the commands pick the agent by tier. Per agent: planner gets Edit + a rework pass (auto re-runs no longer wipe the review) and a split outlet for oversized tasks; the unread Observability score is gone. Plan-reviewer drops Bash/Write, judges the approach first, and its `fix_first`/`regrill` now match auto routing. Implementer learns the frozen test is hash-checked. Reviewer's panelist/arbiter seats stop contradicting its prompt, and test-fixer fixes outside the plan are now reviewed. Test-fixer treats a flake in touched code as a race. Fable 5.1-era prompt lines removed.

- **0.53.1** — **Root README explains the Opus 5.5 switch.** New "Why Opus 5.5" section: the
Opus 5.5 vs Fable 5.1 launch benchmark table, what moved per stage in 0.53.0, and the caveat.

- **0.53.0** — **Opus 5.5 takes every critique seat; Fable and `--opus` are gone.** Opus 5.5 beats
Fable 5.1 on every benchmark Anthropic published at launch (Terminal-Bench 4.0 66.4% vs 55.8%,
CursorBench 57.8% vs 51.8%, …) at 2.5× less per token, so the `reviewer` and `plan-reviewer` agents
now declare `model: opus`, and the `--opus` flag and `review_model` state field are removed (an old
state.md that still carries it is ignored). New effort table: planner **opus/medium**; plan-review
**opus/high** on every tier (trivial no longer skips it) and **xhigh** at critical, always a rung
above the planner; implementer sonnet/medium; repair opus/high; diff-review **opus/high**, **xhigh**
from hard up. Auto follows: plan gate as above, panel sonnet/high (trivial/normal) or opus/high
(hard/critical), arbiter opus/high or opus/xhigh. Statusline and fleet show the tier-sized effort.
`docs/tiering.md` rewritten with the per-step tables and the benchmark comparison.

- **0.52.1** — **Docs caught up with the last three changes.** The `repair` stage is now in the
places that describe the pipeline rather than only the changelog: the stage/agent table, the auto-mode
spec (step 6b, the CI-veto route, "a red suite is not a rework"), `docs/tiering.md` (repair is never
tiered — a red test is a diagnosis, not a matter of doubt), the agent colour legend and the models
section. Fleet's `R` (rebase + the one fenced force push) and ⏎-spawn-from-an-empty-repo are in the
key tables, not just the in-app manual.

- **0.52.0** — **TRINITY: a red suite is a diagnosis problem, not a typing problem.** The
implementer (sonnet/medium) used to own every red test, including the ones it had just failed to
fix — so it looped, and a loop on a test it never root-caused is how tests end up skipped,
loosened or quietly deleted. Now it gets exactly ONE try; a test still red after it goes to
TRINITY, a new `repair` stage running the **test-fixer** subagent on **opus/high** (always —
`--opus` and `review_model` do not reach it). TRINITY reproduces the failure, re-runs it once to
rule out a flake, names the root cause in one line before editing anything, fixes the cause in
production code, and proves both the single test and the FULL suite green. It may never weaken,
skip, `xfail`, retry, widen or delete a test — and the frozen test's tamper hash still guards the
gate. It writes `repair.md` with a verdict: `fixed` · `flake` · `replan` (the approach cannot pass
— bounce to the planner instead of patching) · `needs-human`. Budget: 2 rounds. In auto mode a CI
veto now routes here instead of to the rework loop, which is for review findings only. Sequential
by design: the fixer edits the tree the reviewers read, so it never runs beside the panel.

- **0.51.0** — **An empty repo is a starting point, not a dead end.** Drilling into a repo with no
agents left you on a screen with nothing to select, so `⏎` had no row to spawn from and the only way
forward was `←` back to the overview. Drilled in with no rows, `⏎` now opens the prompt box for that
repo itself (the target is rebuilt from the scan), and the empty screen says so.

- **0.50.0** — **`R`: rebase onto main, force-push one branch.** A branch that has been running for a
day drifts behind `main`, and catching it up by hand means leaving fleet. `R` on a repo, worktree or
session row rebases that checkout's branch onto the default branch and force-pushes it. It is the
only force push fleet performs anywhere, and it is fenced in: `--force-with-lease`, one explicit
`<branch>:refs/heads/<branch>` refspec, never the base and never another ref. It refuses before
touching anything when the checkout sits on `main`/`master` itself, when the tree is dirty, or when
GitHub does not report the base branch as protected — and an answer it cannot get (no `gh`, no GitHub
remote) counts as unprotected, because an unprotected base is what makes a mis-aimed force push
unrecoverable. Conflicts are never resolved for you: the rebase is aborted, nothing is pushed, and
the message hands the job back.

- **0.49.0** — **fleet sees three levels, and worktrees.** Two ways a repo could sit in your
workspace and never get a row. Repos one level deeper than the scan reached
(`workspace/autoretouch/mpe/watermark`) were dropped with the plain dir holding them: they now
flatten into the group as `mpe/watermark`, so the tree still stays two deep. And a checkout whose
`.git` is a *file* rather than a directory — every `git worktree add` and every submodule — failed
the repo test everywhere it was made, so it vanished from the scan *and* sent `workspace_root()`
walking past it to the wrong workspace. `.git` now counts either way.

- **0.48.2** — **One session, one task dir.** The other half of the duplicate-task report: starting
the same work twice under a slightly different slug (`ais-showcase-poses` first, then
`ar-2168-ais-showcase-poses` once the ticket turned up) left two task dirs in the repo, and fleet —
which falls back to the newest state.md — then put both agents on the same task. `feature.sh seed`
now adopts an existing task dir whose slug matches modulo a ticket prefix, in either direction, and
tells the command which key to use; unrelated tasks still get their own dir.

- **0.48.1** — **Two agents in one repo no longer report each other's task.** `state.md` was picked
by mtime, so every session rooted in a repo showed whichever task had been touched last: start a
second agent there and both rows flipped to the same task, stage and tier. The hook now records
which task dir each session actually writes (or the task named in its `/anderson:` command) and
fleet reads that session's own state.md. Sticky across events that say nothing about the task, and
sessions with no hooks keep the old mtime fallback.

- **0.48.0** — **The tier is visible everywhere the work is.** The difficulty tier already decided
what the review gates cost, but you had to dig for it. It now leads the plan (a `**Tier:**` line
directly under the H1, above 🎯 What, instead of buried in the Scorecard), rides the PLAN_REVIEW
banner so you see it before the critique starts, and has its own column on the fleet overview —
`triv · normal · HARD · CRITICAL`, upper-case for the two that buy a heavier review — so a screen of
rows shows at a glance which agents are grinding and which are coasting.

- **0.47.0** — **A busy repo gets a worktree, not a hijack.** Spawning an agent onto a repo that is
already parked on a feature branch used to drop it straight into that checkout, on top of whatever
was in flight there. Now the agent gets its own worktree — `.worktrees/<task>` on `anderson/<task>`,
cut from the default branch (`origin/<default>` when it exists) — and the repo keeps its branch and
its uncommitted work. On the default branch nothing changes: the checkout is free, the agent uses it.
Anything git refuses falls back to the repo with a note, so a spawn is never blocked. Sessions
running in a worktree still row under the repo they came from, not in `elsewhere`.

- **0.46.0** — **The monitor stays put, and you can hide a repo.** Spawning an agent used to take
over the window fleet was in: it now opens a terminal of its own (a real OS window on macOS, a `-d`
tmux window elsewhere), so the fleet you launched from is still there when the agent starts. The
prompt box was a dim quote line nobody could find while typing, and is now a solid bar with a block
cursor. `b` on a repo or group row hides that repo and its agents, saved per workspace like order and
collapse; `h` lists the hidden ones, folded and dim, and `b` brings one back.

- **0.45.0** — **`fleet update` updates the plugin.** The shim in `~/.local/bin` already resolves the
newest cached version at run time, but nothing told you a newer one existed, so a machine could sit on
an old fleet for weeks. `fleet update` now refreshes the marketplace, updates the plugin through the
`claude` CLI, and prints the version it moved from and to (or that you were already current); restart
Claude Code to apply. No `claude` on PATH, it points you at `/plugin update anderson` instead.

- **0.44.0** — **Fleet becomes the place work starts.** Rows are now the repos of the workspace fleet
was launched from, one nested level, with live sessions underneath their repo and collapsible groups.
`J`/`K` order and the collapsed set persist per workspace, and `⏎` on a repo or group row spawns a
claude agent into it as a tmux window, so the monitor no longer needs an IDE to begin work in.
Behaviour change: `fleet` outside tmux attaches a per-workspace tmux session by default, and
`⏎ · J/K · space · D` have new meanings.

- **0.43.0** — **It counts its own installs.** A marketplace install is a shallow clone, which GitHub's
traffic API counts; an update is a fetch, which it does not. So the plugin says hello once per version
per machine: a SessionStart hook fetches the one-byte `ping` asset attached to that release, and
GitHub's public `download_count` on the asset is the number. Nothing is sent but the request itself —
no identifier, no path, no machine or user information, no third-party service. Opt out with
`ANDERSON_NO_TELEMETRY=1` or the cross-tool `DO_NOT_TRACK=1`, and the hook never runs. See
[Install counting](#install-counting).

- **0.42.0** — **The plan states its own price.** The tier decided what the review gates cost and
which models ran them, but only `state.md` knew it. `plan.md` now carries a `**Tier:** <TIER> —
plan_review <model>/<effort> · implement sonnet/medium · diff_review <model>/<effort>` line under
`## 📈 Scorecard` (the planner seeds it `pending`; routing fills it in, the plan-reviewer leaves it
alone), the Gate 1 card echoes the same line, and the re-tier at the diff gate rewrites both with
`was <old>` when it escalated — so a silent price change is no longer possible and you see the bill
before you approve it. Also fixes a stale README footnote that still claimed diff-review effort was
a fixed `high`/`xhigh` off Risk ≥ 8, which tiering replaced in 0.40.0.
- **0.41.0** — **Fleet: ⏎ revives a sentinel.** A dead row had nothing to jack into, so 0.40.2 told
you to press `c` and paste the command yourself. Now `⏎` gives that session a terminal: a new tmux
window when fleet runs under tmux, else a new iTerm2 / Terminal.app window (AppleScript; a Ghostty / iTerm2 tab since 0.57.1), already
running `cd <cwd> && claude --resume <sid>`. `c` still copies, and off macOS/tmux — or when
AppleScript is refused — revive falls back to that copy with the reason.
- **0.40.4** — **Fleet: the AXRaise fallback goes.** 0.40.2 retried a failed raise through System
Events AXRaise. Measured against a real cross-Space window it never helped: AXRaise cannot pull a
window off another Space, and aiming it needs a window title, which in Terminal carries the running
command and changes between the lookup and the raise (`Can't get window 1 of process`). One 2 s wait
replaces the two-stage retry, and when the window really did stay put the message carries the whole
one-time fix, `killall Dock` included: without that restart the `workspaces-auto-swoosh` default is
written but not live, which is exactly how a jack in needed two presses.
- **0.40.3** — **Fleet: ⏎ across Spaces lands on the first press.** Raising a window that lives on
another Space costs a full-screen Spaces animation first, about a second, and the 0.6 s check added
in 0.40.2 gave up before it finished: the first ⏎ reported that the window had stayed behind, and a
second ⏎ then worked because the Space had already changed. The check now waits up to 1.4 s, retries
through AXRaise, and waits 1.6 s more, exiting the instant the tab is in front — a same-Space jack in
still returns in about 0.3 s.
- **0.40.2** — **Fleet: ⏎ actually moves you there.** Three fixes to the jack in. The focus script
now `activate`s the terminal *before* reordering its windows: with one tab per window (six Terminal
windows, say) activating afterwards handed the raise back to the app's own front window. The result
is then verified — the frontmost tab's tty, not the AppleScript's "ok", which is reported for
selecting a tab whose window never came over — and on a miss it retries once through AXRaise before
saying the window stayed on another Space, with the one-line `defaults write
com.apple.dock workspaces-auto-swoosh` fix. And ⏎ on a dead row now says the process is gone and
points at `c` / `b`, instead of talking about tmux.
- **0.40.1** — **Fleet: ⏎ means move me there.** Jacking into a session parked at a human gate no longer
reports "no IDE owns that session" when a plain terminal owns it: the auto-open is silent unless a GUI
editor actually applies, so a successful jack in stops reading like a failure. `O` still says why nothing
opened, since asking for the IDE is the point of that key. Landing images in both READMEs are now real
stills of the fleet boot screen and the live board (`assets/*.tape` on the `media` branch re-records them with VHS), replacing
the hand-maintained ASCII mock.
- **0.40.0** — **Tiered review effort in start mode.** The gated loop derives plan-review and diff-review
effort from the plan Scorecard instead of running both at a fixed xhigh: a trivial tier skips plan-review,
critical runs both gates at xhigh.
- **0.39.0** — **Fleet: see what the subagents are doing.** On a tall terminal the card lists the running subagents
live under `agents` (`↳ anderson:reviewer "Diff-review AR-2598" · ▶ Grep process_order · 40s`), read from their
own transcripts in `<session>/subagents/`. `a` pages the newest one (running first) as a readable log: its words,
the tools it called, a line of each result. `q` returns.
- **0.38.4** — **Fleet: one row per session, really.** Claude Code's background daemon (`claude daemon` →
`bg-spare`, `bg-pty-host`) runs under your session with its own session ids and fires the same hooks, so a
session could show up three times. Any session whose process descends from another claude process is now
folded away, whether fleet found it by ps or by its hook / heartbeat files.
- **0.38.3** — Fleet: `o` with glow now uses the full terminal width (glow wraps at 80 columns unless told).
- **0.38.2** — **Fleet: idle goes white.** A ring older than 5 minutes stops pulsing and paints white, steady;
it still sorts with the rings and still needs you, it just stopped shouting. Fresh rings pulse as before.
Also repairs the changelog: a careless version bump had rewritten the number on every entry since 0.34.4.
- **0.38.1** — **Fleet: extras installer + requirements list.** `fleet install` reports the optional tools
(glow, terminal-notifier, tmux) with ✓ / missing and the exact install line; `fleet install --extras` installs
glow and terminal-notifier, `--all` adds tmux. `/anderson:fleet` now forwards its flags (`--extras`,
`--with-tmux`, `--all`). New "What fleet needs" table in both READMEs.
- **0.38.0** — **Fleet: read the plan where you are.** `o` now opens plan.md / audit.md inside the fleet terminal
(glow when installed, else `less -R` over a small stdlib markdown colouring: headings, bullets, **bold**, the
reviewer's ~~strike-through~~, code); `q` comes straight back. `O` keeps the IDE route (--editor, GUI $VISUAL,
or the IDE owning the session). Sessions owned by a plain terminal no longer fall back to `open` into whatever
app claims .md files; they say so and point at `o`.
- **0.37.5** — Fleet: full repaint every 10 s and on ctrl-L. The diff repaint only redraws lines it knows changed,
so a Space swipe or an app switch that made the terminal drop cells left stale garbage until the next resize.
- **0.37.4** — Fleet: one more blank line between the list's rule and the card on tall terminals.
- **0.37.3** — **Fleet: room to breathe, part two.** On a tall terminal (16+ free lines) blank lines sit around the
header rule and between the list and its rule; short terminals stay dense.
- **0.37.2** — **Fleet: usage moves to the top.** The plan's windows now sit right under the title, with a bar each
(`matrix · session ▓▓▓▓░░░░░░ 42% · 3h39 left │ week ▓▓▓▓▓░░░░░ 52% · resets Fri 19:00`), red past 90%. The footer
keeps the keys only; API-key users (no windows) still see the api estimate down there.
- **0.37.1** — **Fleet: no ping when you're already there.** A ring skips the desktop banner and the sound when the
session's own terminal is frontmost (the Terminal.app / iTerm2 tab showing its tty, the active pane of an attached
tmux session, or the IDE that hosts it); the toast in fleet still says who needs you. `fleet --ping` sends a test
banner through every channel and says where to look in System Settings when none shows.
- **0.37.0** — **State first.** `/anderson:start` now seeds `feature-research/<task>/state.md` in a shell preamble,
before the model reads a single line, so the fleet row (task, ARCHITECT, plan 0/2) appears within two seconds
instead of after the planner warms up. New `feature.sh seed [--opus] <task>` does exactly that and nothing else
(idempotent: an existing state.md is left alone).
- **0.36.2** — **Fleet: `h` shows the hidden rows** (flagged `◌`, dim, counted in the header); `b` on one brings it
back. A few footer keys wear a marker so the eye finds them: 🔴 kill · 🔵 hide · 👻 hidden · 🔔 notify ·
🔊 sound · 🎵 ring · 🔍 filter · 🎨 theme (unicode terminals only; `--ascii` stays plain).
- **0.36.1** — **Fleet: kill hides, hide never kills.** `r` (kill, asks first) now hides the row as soon as the signal
is out; `b` hides any row, live or dead, without touching the process (a hidden live session stays hidden).
Footer says `r kill · b hide`; the pills live on in the manual and the toasts.
- **0.36.0** — **Fleet: the footer moves to the floor.** Keys and usage now sit on the last lines of the terminal, each on
its own line (keys wrap between groups, never truncate; usage reads alone). The detail card keeps the whole middle.
New `agents` line in the card: how many subagents the session sent, how many are running, and the last one
(`4 sent · 1 running · last anderson:reviewer "Diff-review AR-2598" (fable)`), read from the transcript's
`subagents/` folder.
- **0.35.1** — `fleet --play all` auditions every ring sound from the shell (`--play NAME` for one); `--rings` says so.
- **0.35.0** — **Fleet: pick your ring.** Seven bundled sounds in `assets/sounds/` (phone, the Matrix call, stays the default;
plus snare, hitech, freeze, blip, rift, jump, each cut to its loudest ≤2.5 s and normalized). `s` cycles with a
preview and saves the pick, `--ring NAME` / `--rings` from the shell, and any `.wav` you drop in
`~/.claude/fleet/sounds/` joins the list by name. `~/.claude/fleet/ring.wav` still overrides everything.
Licenses in `assets/NOTICE.md`.
- **0.34.4** — **Fleet: one process, one row.** Headless `claude -p` children spawned inside a session (reviewers, hooks) no longer show up as a second session of the same repo, and after `/clear` or `/resume` only the process's current session id is listed.
- **0.34.3** — **Fleet: room to breathe.** With 16 or more free lines the detail card goes airy:
  blank lines between the three groups (task · who · verdicts │ status · context · where │ prompt ·
  last · next), an 11-cell label column, and `last` wraps to two lines instead of truncating. Ten to
  fifteen free lines keep the compact card; fewer keep the three-line form.
- **0.34.2** — **Fleet: one full ring.** The bundled phone is now exactly one ring (2.43 s, 0.97 s →
  3.40 s of "Full Matrix", boundaries found by energy scan) instead of a 1.25 s cut that stopped
  mid-ring. Same CC0 source, cut from the Pixabay copy of the file.
- **0.34.1** — **Fleet: the Matrix phone.** The ring is now a 1.25 s cut of the telephone ring from
  "Full Matrix" by skycarl (Freesound #210499, **CC0**), bundled as `assets/ring-matrix.wav` with
  attribution in `assets/NOTICE.md`. Precedence: your `~/.claude/fleet/ring.wav`, else the bundled
  phone, else the synthesized ringback.
- **0.34.0** — **Fleet: the phone rings; honest usage numbers.** `m` (or `--sound`) plays a
  synthesized ringback tone (440 + 480 Hz, two bursts, stdlib-generated into
  `~/.claude/fleet/ring.wav`, replace the file for your own sound) when a session starts waiting on
  you; `afplay` on macOS, `paplay` / `aplay` on Linux. The footer's `/usage` windows are the last API
  reply any session saw, since fleet cannot query the API itself: numbers older than two minutes now
  carry `(as of 4m ago)`, and copies older than six hours are dropped rather than shown wrong.
- **0.33.1** — **Fleet: detail card; red footer at 90% usage; test fix.** When the terminal has
  ten or more free lines below the table, the selected session gets a labelled card instead of three
  dense lines: `task` (with repo and `⎇ branch`), `who` (persona · stage · model · tier), `verdicts` (plan,
  diff, gate), `status` (what it does now, last activity, session age), `context` (bar, tokens,
  lines ±, `← /compact` past 80%), `where` (pane, pid, session id), `prompt` (first prompt when an
  anderson task is running), `last` (last words), **`next`** (the one thing you do now: which command,
  which file). Small terminals keep the compact form. The footer paints red when any `/usage` window
  passes 90%, since extra-usage credits come right after. 0.33.0 shipped with one failing test (an
  exact-dict prefs assertion that predates the `editor` pref); fixed, and the release pipeline now
  merges only on green CI.
- **0.33.0** — **Fleet: open the gate artifact in your IDE.** `o` opens what the current stage wants
  read: `plan.md` for grill and plan review, `plan.md` + `audit.md` for diff review, `audit.md`
  during implement. Jacking into a row parked at a human gate (`gate: human`) does it automatically,
  so `⏎` lands you in the session *and* on the plan. Editor resolution: `fleet --editor code`
  (saved), else a GUI `$VISUAL` / `$EDITOR` (code, cursor, zed, subl, webstorm, idea, pycharm…), else
  the IDE that owns the session (WebStorm / VS Code integrated terminals), else the OS default opener.
- **0.32.2** — **Fleet: reliable macOS notifications.** `osascript` banners are often swallowed on
  recent macOS and never register an app in System Settings. `notify()` now prefers
  `terminal-notifier` when installed (`brew install terminal-notifier`): banners show, the app is
  listed under Notifications, and clicking one brings the terminal fleet runs in to the front.
  Pressing `n` sends a test banner and, when the tool is missing, says how to install it;
  `fleet install` prints the same hint on macOS.
- **0.32.1** — **Fleet: context alert.** When a live session crosses 80% context the monitor toasts
  `context 84% on <repo> · <task>: /compact before it eats the budget`, and pings the desktop when
  `n` notifications are on. Once per crossing; a `/compact` that drops it below the line re-arms it.
- **0.32.0** — **Fleet: navigation and overview batch.** Sessions with no anderson pipeline show
  their first prompt as a quoted title instead of `(no anderson task)` (a `/resume` summary wins when
  Claude Code wrote one; titles survive on sentinels so you know what to resume). Ringing rows say
  for how long: `☎ ring 12m`, `☎ permission Bash 3m`, `☎ idle 4h`. The ctx cell paints red past 80%
  (`/compact` before the next review panel). Rows are numbered; `1`..`9` jack straight into row N.
  `c` copies `cd <cwd> && claude --resume <sid>` to the clipboard (pbcopy / wl-copy / xclip, else
  shown), so a sentinel is recoverable, not just dismissable. `⎇ branch` in the detail line now
  comes from the transcript's `gitBranch` for every session, not only anderson ones. `n` (or
  `--notify`) turns on a desktop notification when a session starts ringing (macOS Notification
  Center, Linux `notify-send`), saved in prefs.
- **0.31.2** — **Fleet: closed sessions die on screen.** A session whose emitter never recorded a
  usable pid (files written before 0.31.1, or a session older than the hooks) had no liveness
  signal, so closing it left the row up until the 24h expiry. Now: pid unknown + no `claude` process
  in that cwd = `✝ sentinel`. `b` still dismisses it.
- **0.31.1** — **Fleet: real pids, no duplicate rows, idle detection, column caps.** The heartbeat
  and hook emitters reported pid 1: the backgrounded emitter is reparented to launchd, so `getppid()`
  lied. Effects: sessions never became sentinels, `ps` discovery added a duplicate row for the same
  session matched to a stale transcript, jack-in by pid failed. Emitters now walk the ppid chain to
  the real `claude` process (`FLEET_PID` handed down by the statusline shells); fleet treats pid ≤ 1
  as unknown and adopts the `ps` process in that cwd instead of duplicating. A "thinking" session
  with no transcript activity for 15 minutes is shown as `☎ idle` (interrupted turn, waiting on you).
  Repo/task columns cap at 28/56 cells so ultra-wide terminals stay readable.
- **0.31.0** — **Fleet: usage in words, `$` opt-in, `fleet` runs in place.** Footer now reads
  `session 46% · 4h07 left │ week 41% · resets Fri 19:00` (the `/usage` windows: the rolling 5-hour
  "current session" and the 7-day all-models window; Claude Code exposes no per-model weekly number
  and no plan price, so on a flat-fee plan these percentages are the cost). The `api$` column and
  footer estimate are hidden on subscriptions; `$` or `--cost` shows them as a burn gauge; API-key
  users (no limits) still see them by default. `fleet` now runs in the current terminal whether or
  not tmux is around; `fleet --tmux` opts into the persistent tmux session, with its status bar off.
- **0.30.1** — **Fleet: zoom.** Font size belongs to the terminal, and Terminal.app exposes it per
  window over AppleScript, so `fleet --zoom 16` (or `+` / `-` while running) grows the window's font
  for the monitor and restores the original size on quit. Saved in `prefs.json`; `--no-zoom` clears.
  iTerm2 and IDE terminals have no font API: the toast says ⌘+ / ⌘-.
- **0.30.0** — **Slugs with a slash stay flat; ship on that branch.** Pasting a branch name as the
  slug (Linear style, `user/ar-2587-ui-polish`) used to nest the state dir
  (`feature-research/user/ar-2587-…/`), invisible to the statusline, the scheduler, `/anderson:status`
  and the fleet monitor. The task key is now the LAST `/`-segment, so the dir is always
  `feature-research/<key>/`. When the slug had a `/` it is recorded as `branch:` in state.md and
  `approve-diff` / `feature.sh --approve-diff` ship on it verbatim instead of `anderson/<key>`, so
  the branch matches the ticket. Every command resolves the key the same way; fleet's detail line
  shows `⎇ <branch>`. `test/test_feature_slug.py` proves flat dir, `branch:` seed, and ship branch.
- **0.29.3** — **Fleet: subscription usage in the footer; honest `$`.** The heartbeat now records
  Claude Code's `rate_limits` (the `/usage` numbers: 5-hour and 7-day windows, used % and reset time)
  and the footer shows them: `zion $115.28 · 5h 20% ↻4h33 · 7d 37% ↻Fri`. Account-wide, so the
  freshest heartbeat is the truth. The `today $` total is gone: it summed lifetime per-session costs
  and read as a daily bill. `$` is documented for what it is, Claude Code's client-side estimate at
  API list price, notional on a subscription, a gauge of which session burns most.
- **0.29.2** — **Fleet: jack in reaches IDE terminals.** When a session runs in an integrated
  terminal (WebStorm, VS Code, Cursor, Warp...) no tab is scriptable, so `⏎` now walks the process
  ancestry to the owning `.app` and brings it forward, with a toast saying the tab itself could not
  be selected. Order stays: tmux pane → iTerm2/Terminal.app tab by tty → owning app.
- **0.29.1** — **Fleet: jack in without tmux; tmux optional.** `⏎` now falls back to the session's
  tty: on macOS it focuses the iTerm2 / Terminal.app tab that owns the Claude process (AppleScript),
  so sessions started in plain terminal tabs are one keypress away too. When the monitor runs outside
  tmux and the session is in a pane, the pane is selected and the tab holding that tmux client is
  focused. `fleet install` no longer assumes tmux: it says tmux is optional and offers
  `fleet install --with-tmux` (brew / apt / dnf). Manual, card and READMEs follow.
- **0.29.0** — **THE OPERATOR: `bin/fleet.py`, the cross-repo fleet monitor.** One terminal for
  every Claude Code session on the machine: repo, anderson task, persona on the job, stage, model,
  what it does right now, $, context, age; ⏎ jacks into the session's tmux pane. Runs outside Claude
  (stdlib curses, zero tokens). Zero-setup discovery via `ps` + transcript tail + `state.md`; this
  plugin's hooks add the exact waiting/working signal (`hooks/fleet_event.py`); the statusline
  heartbeat (`bin/heartbeat.py`, called by `statusline.sh` or the new `fleet-statusline.sh` wrapper
  around any statusline) adds cost and precise context. Five themes (`matrix`, `construct`, `zion`,
  `nebuchadnezzar`, `agent`), Matrix-or-plain wording and motion are per-user prefs in
  `~/.claude/fleet/prefs.json`. Repaints only changed lines (no flicker). Alignment is a tested
  invariant (`--selftest`, `test/test_fleet.py`). Boot screen with a line that rotates every launch.
  `/anderson:fleet` installs the `fleet` launcher (tmux-aware, stable across plugin updates) and prints the card. Loop unchanged.
- **0.28.0** — **Fable is the default critic; `--fable` becomes `--opus`.** The `reviewer` and
  `plan-reviewer` agents now declare `model: fable` in frontmatter, and `review_model` seeds to
  `fable`; the inverse flag `--opus` (on `start`, `auto`, `feature.sh start`) runs both critique
  gates on Opus instead. Rationale: Fable is the stronger critical analyst, and Fable 5.1 cache
  reads are priced far below prior tiers, so the plan + diff context re-read by the panel and
  arbiter is cheap to serve. Generative stages (planner opus, implementer sonnet) unchanged.
  Missing `review_model` in an older `state.md` now resolves to `fable`. Banners, matrix demo,
  statusline fallback, and both READMEs follow. **Reviewer effort tiered:** `reviewer` frontmatter
  drops to `high`; `xhigh` only for hard/critical panelists, the arbiter, and gated diff reviews where
  the Scorecard has Risk ≥ 8 or the change touches security / memory / OS boundaries. Plan-reviewer
  stays `xhigh`. **Two Fable 5.1 prompt snippets** (from Anthropic's prompting guide): both reviewers
  batch independent reads into one turn; the plan-reviewer edits `plan.md` surgically instead of
  rewriting it.
  **Prompt audit** (`/claude-api prompt-audit`): quote-selection arithmetic replaced by "pick one",
  duplicated quote pools collapsed, `auto.md` override-policy changelog rewritten as current rules,
  sequencing/banner rules restated once at normal volume, dead self-review reference and attribution
  asides removed. −130 lines of command surface. Bench (2×2, same fixture, `/anderson:approve-plan`):
  sequencing held in 4/4 runs; reviewer verdict vocabulary now valid in 2/2 (was `rework` 2/2 before);
  cost −36%, wall time −40% (confounded with the reviewer effort drop).
- **0.27.0** — **Dated model IDs removed, per-token prices dropped, persistent override
  documented, statusline follows the active review model.** The two dated model-ID strings in
  `docs/auto-mode-handoff.md` are gone, along with the per-token figures next to them — a new CI
  step now fails the build if any tracked file quotes a paired per-token price. `settings.json`
  `env` (`CLAUDE_CODE_SUBAGENT_MODEL` / `ANTHROPIC_MODEL`) is documented as the supported way to
  pin every stage to one model permanently, not a gotcha to clear. The statusline now reads the
  active review model (`fable`/`opus`) instead of always showing Opus under `--fable`. Version
  sites re-synced across `plugin.json`, `marketplace.json`, and both README badges.
- **0.26.0** — **Outcome-shaped criteria, load-bearing assumptions, one proof per criterion, and
  multi-repo contract verification.** Acceptance criteria are now observable outcomes (`When X → Y`,
  actor's POV — never a restated How), capped to what's provable AND load-bearing. `## ✅ Decisions`
  classifies each assumption **LB** (feature is wrong if the guess is wrong) or **safe**; the plan
  gate **blocks** while any LB row is unconfirmed (gated: the grill can't defer it; auto: the
  plan-reviewer ratifies with a basis or ships it as `needs-human`) — a guessed target can no longer
  pass every downstream check. Every criterion now needs its OWN discriminating proof that fails if
  that criterion breaks (no shared/blanket evidence, no `#n covered by #m`) — the silent
  edge/failure-case bug now needs executable proof, not a reviewer's eyeball. Multi-repo tasks gain a
  mandatory `source: contract` seam criterion proven against a frozen fixture both repos pin, a
  `⚠️ Merge order` line on the primary PR, and `Blocked by` links on companions. `visual` proof is
  state-driven (a screenshot per outcome-state, not one happy-path shot).
- **0.25.0** — **⚠️ Behavior change section + design moves up.** The planner adds a `## ⚠️ Behavior
  change` line (≤2 lines: the "so what" — what observably changes for a user/caller/API, or
  "none — internal only") right after Why. New plan read order: What → Why → ⚠️ Behavior change →
  🗺 Design → ✅ Acceptance criteria → 🛠 How → 📈 Scorecard (Design promoted above the criteria).
  Both ship paths carry the behavior-change line verbatim into the PR body (omitted when
  internal-only) and match the same order (Design before criteria). **Proof is now displayed,
  not just named:** the implementer tees each e2e run to `evidence/*.e2e.log`; both ship paths
  embed that log in a per-criterion `<details>` collapse under the criteria table (the ephemeral
  script's only record — it never reaches CI), and post visual screenshots as a PR comment
  (gist-hosted, since `gh` can't inline-upload), degrading to the gate-verified text note on any
  failure. Test proofs stay named-only — the diff + CI already show them.

- **0.24.0** — **PR body is the plan minus the how.** Both ship paths (`/anderson:approve-diff`
  + `/anderson:auto` step 8d) now build the PR from the plan's durable sections instead of dumping
  the whole plan into one collapse. Visible, in read order: What & why, the acceptance-criteria
  table with evidence, the design (lifted out of its plan collapse), and a reviewer-facing
  **How to test** section — the test command, manual steps, and a `**Config required:**` line for
  new env vars / flags / deps. Scorecard, blast radius, and error handling drop into `<details>`
  collapses below. The **🛠 How and ✅ Decisions are excluded** — the diff is the how, no double-up.
  Open-questions still print only when there are deferred business calls. The old verbatim "Full
  plan" collapse is gone: the structured sections are now the plan's durable GitHub home.
- **0.23.0** — **Acceptance criteria with proof, design intake, and a leaner read.** Three
  moves, one theme: verify against explicit criteria instead of vibes, and show humans only
  what they need.
  - **✅ Acceptance criteria table** (`# | Criterion | Source | Proof | Evidence`) is now the
    plan's spine, in BOTH modes. Sources: `ticket` (verbatim), `design` (exact strings from the
    design inventory), `derived` (planner judgement — the gated grill confirms each as a 🔴
    question; auto's plan gate checks coverage as before). The plan-reviewer blocks on a
    missing table, an unmapped criterion, or paraphrased design copy.
  - **Design intake** — `/anderson:start` (step 2b) and `/anderson:auto` (step 1g) normalize
    any referenced design — Figma URL, ticket screenshot, or image file — into
    `feature-research/<task>/design/` (PNGs + `inventory.md`: every exact string, state, and
    layout fact). Fixes the "built it, doesn't match the design" gap at its root: the criteria
    and the reviewer now have the reference artifact.
  - **Evidence or it didn't happen** — the implementer must fill the Evidence column (its only
    permitted plan.md edit): `test` (must fail without the change), `visual` (screenshot of the
    running UI into `evidence/`, compared against `design/` by the reviewer), `e2e` (ephemeral
    script in scratch — gate-time only, deleted at ship, never wired into CI; `promote
    candidate` flags a flow worth keeping), or `manual` (only when nothing executable covers
    it). The diff reviewer gained a blocking **criteria-evidence lens**: runs the tests, opens
    the visual pairs, blocks on blank cells, worthless tests, or any text/layout mismatch —
    reported as `criteria: proven/total`. Auto's correctness panel lens carries the same check.
  - **Leaner plan.md** — human-first read order (What → Why → Criteria → How → Scorecard
    visible; Design / Blast radius / Error handling / Decisions bodies in `<details>`
    collapses) with hard word budgets the plan-reviewer enforces. Fewer tokens for every
    downstream agent, not just fewer lines on screen.
  - **Gate TL;DR cards** — both gates now halt on a card (what · criteria/proof counts ·
    scorecard · verdict; Gate 2 lists failed criteria with the reviewer's one-line why), so
    reading the full plan becomes the exception.
  - **Leaner PR body, both ship paths** — visible: Source (when present) · What & why ·
    criteria table with evidence · scorecard; Setup and Open-questions print ONLY when
    non-empty; How-to-test is absorbed by the evidence column + one `test:` line; review
    detail, audit, metrics, and the full plan stay in collapses. Gated `state.md` gains
    `source_url:` (additive) so the ticket link survives to the PR.
- **0.22.0** — **`/anderson:help` quick-reference card.** New one-shot command that prints a static
  card with every command, its arguments, the two gates, and the `--fable` flag. Reads no state,
  spawns no agents — the live dashboard stays `/anderson:status`. Both READMEs' command tables
  gained the row.
- **0.21.0** — **Plan-reviewer judges the frame first.** Before line-editing, the plan-reviewer
  now asks "would I have planned it this way?" — a wrong approach gets rewritten in place (with
  read scope widened to what the rewrite needs) or routed `regrill`, instead of being patched
  line by line. Closes the anchoring gap in the `--fable` review gate.
- **0.20.2** — **Grill instruction cleanup.** Removed the now-redundant "assume I know the code"
  instruction bullet: the 3-line question card already enforces terse, context-free questions and
  the 🟢 batch handles preferences, so it was saying twice what the format already guarantees.
  Behavior is unchanged; the grill still never asks about code familiarity.
- **0.20.1** — **Grill drops the familiarity question.** The grill no longer opens with the
  "How familiar are you with <touched area>? wrote it / know it / new to it" calibration line. It
  now assumes you know the touched code: terse questions, no per-question context sentences,
  borderline 🟢 auto-resolved to the recommendation. One less meta-question before the real ones.
- **0.20.0** — **Slimmer, calmer grill.** The interrogation step was too busy — a 3-line manifest
  with a per-vector "blindspot sweep" line, two-line question headers, and eight competing emoji.
  Now: a **one-line manifest** (`grill · N questions · a🔴 b🟡 c🟢` + a rule), and each question is
  a **3-line card** — `🔴 n/N ▰▰▱▱▱▱▱▱▱▱` (the grade dot is the only emoji; the bar is 10 cells,
  filled = round((n−1)/N × 10) so it grows as answers land), the question, then `→ recommendation`.
  When an answer spawns a new question the total grows in place with a dim `+1 from your last
  answer` note — no manifest reprint. **The standalone blindspot sweep is gone**: the planner
  already maps blast radius at plan time, so the grill now challenges that table's completeness
  directly (grepping a specific caller only when it doubts a row) instead of re-sweeping five
  vectors on every run. Less ceremony, same catch, a screen you can think in.
- **0.19.0** — **`--fable` opt-in for the review gates.** New state field `review_model` (default `opus`)
  runs the two critique stages — PLAN GATE plan-reviewer, DIFF GATE reviewer panel + arbiter — on Fable
  instead of Opus when a pipeline is started with `--fable`. Fable is the stronger critical analyst; the
  generative stages (planner, implementer) stay on Opus/Sonnet and the flag never touches them. Effort
  stays xhigh. The choice is seeded once at pipeline init and persists in `state.md`, so it carries across
  the resumed `approve-plan`/`rework` sub-commands; `feature.sh start … --fable` and `/anderson:auto …
  --fable` both honor it. In auto mode the panel's HARD/CRITICAL tier + arbiter follow `review_model`
  (`panel_model` metric gains a `fable` value); TRIVIAL/NORMAL panelists stay on the cheap tier.
- **0.18.0** — **Ponytail ladder + caveman-compressed instructions.** Two token cuts, different axes:
  - **Ponytail decision ladder** (after [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail),
    MIT) inlined into all four agents — anderson stays self-contained, no plugin dependency. Before any
    new function/module/abstraction/dependency: does it need to exist? → already in the codebase? →
    stdlib/platform? → existing dep? → one line? → only then minimal new code. Planner plans least-code,
    implementer writes least-code (no speculative params, no single-call-site helpers), plan-reviewer
    edits excess down in place, diff-reviewer runs a YAGNI lens (blocking when excess adds a dependency
    or public surface). Safety rungs exempt everywhere: validation, security, accessibility, error
    handling are never cut. Less code generated = fewer output tokens now, fewer input tokens every
    later read of that code.
  - **Caveman-compressed command prose** — instruction files are input tokens paid on EVERY run;
    compressed instructional prose only (articles/filler dropped, duplicate sentences merged), all
    byte-faithful blocks untouched: quote pools (3×24 verified), state.md template + STATE markers,
    banners, git/gh command lines, verdict values. start.md −12% chars (the quote-picking algorithm,
    repeated verbatim per banner, is now one QUOTE RULE + per-banner offset); approve-plan −6%,
    rework −5%, approve-diff −4%, auto.md −2% (deliberately conservative — it runs unattended).
    Single revertible commit in case compliance regresses. **Graded grill with upfront triage.** The grill previously streamed questions
  open-endedly: no sense of how many were coming, which ones mattered, and only questions the plan
  already knew it had (its own decision tree) ever got asked. Now:
  - **Triage first** — THE INTERROGATOR enumerates every question in one pass (decision-tree
    branches + 🧯 `needs-context` rows + 💥 blast-radius gaps) **plus a structured blindspot
    pass** over what plan.md never mentions, sweeping five concrete vectors (callers, tests,
    config/flags, git history, repo conventions) rather than one free-form look — the manifest's
    sweep line (`callers ✓ · tests +2 · …`) proves each vector was checked. Anything the
    codebase can answer is answered there, never asked.
  - **Calibration (question 0)** — one line, "wrote it / know it / new to it", tunes question
    depth to your familiarity with the touched area; never more than this one meta-question.
  - **Token economy** — the sweep is scoped to the plan's touched files/symbols (grep/git-log
    one-liners, excerpts, no repo-wide scans), preferably delegated to one cheap read-only
    search subagent so the greps never enter the main session's context; trivial plans collapse
    it to a single grep + git-log pass. Turn count cut too: independent 🟡 pair 2–3 per message,
    each question capped at 4 lines (header + question + recommendation, no plan restating).
  - **Grades** — every question is classed 🔴 ARCH (answer changes architecture/data model/scope),
    🟡 BEHAVIOR (edge cases, error handling, UX semantics), or 🟢 PREF (safe to default).
  - **🔥 Manifest** — printed before question 1, so you see the grilling level upfront: total count,
    per-grade split, and the per-vector blindspot sweep line.
  - **Progress header** — each question carries `❓ n/N · grade` + a bar; follow-up questions grow
    N honestly instead of hiding the drift. Order is strictly 🔴→🟡→🟢 (early answers constrain
    later ones); all 🟢 are batched into one message a single "defaults fine" accepts.
  - **Early exit is now safe** — "good, go to review" auto-resolves remaining 🟢 to recommendations
    (`[answered] … (grilled, default)`) and records remaining 🔴/🟡 as `[open]`; skipping never
    silently decides the big ones.
  - `/anderson:demo` annotated to match. (Same triage/grade/manifest model also backported to the
    standalone `grill-me` / `grill-with-docs` user skills, minus state.md bookkeeping.)
- **0.16.0** — **Open-questions parity for the gated path.** 0.15.0 wired the 🧯 error-handling →
  open-questions flow into `auto` but only half into the gated loop: THE INTERROGATOR *walked* the
  `needs-context` rows in the grill, but a deferred row had nowhere to be recorded and never surfaced
  in the ship PR (it survived only buried in the full-plan collapse). Now symmetric with auto:
  - **`/anderson:start`** — the seeded `state.md` gains an `open_questions:` field + a
    `## ❓ Open questions` section. The grill records each row it resolves or defers there, using
    auto's convention (`[answered] … → … (grilled)` / `[open] … — <why>`), and sets the count.
  - **`/anderson:approve-diff`** — the PR body now leads with a visible `## ❓ Open questions &
    assumptions` block (🔴 deferred / 🟢 resolved) lifted from `state.md`, so a reviewer sees the
    open business calls without unfolding the plan; the PR is labelled `needs-human` when any
    `[open]` row remains (graceful — drops the flag if the label or `gh` is unavailable).
  - **`/anderson:demo`** — annotated so the dry-run preview reflects the grill's 💥/📈/🧯 walk and
    the open-questions section the ship PR now carries.
  - Headless `bin/feature.sh` is unchanged (it has no grill stage, so it can't produce open
    questions the same way).
- **0.15.0** — **Error handling as a planning concern + auto-mode open-questions report.**
  - **🧯 Error handling section (planner)** — every plan now enumerates the failure paths the change
    touches (derived from the blast radius, not guessed) and classes each `deduced` (handle it now)
    or `needs-context` (a business call the code can't make). Anchored in THE ARCHITECT, folded in
    silently — no new persona, no new stage.
  - **Verified at both gates** — THE ORACLE (plan-reviewer) treats a missing failure path or a
    `needs-context` row not mirrored in ✅ Decisions as **blocking**; the diff-review correctness lens
    (AGENT SMITH, gated + auto panel) checks every `deduced` row is actually handled.
  - **Gated** — THE INTERROGATOR walks the `needs-context` rows in the grill: you decide the handling,
    the row re-classes to `deduced`.
  - **Auto** — no grill, so step 4g captures the ambiguities into state.md `## ❓ Open questions`
    (`[open]` = needs a human, `[answered]` = auto's assumption). They surface in a new PR section
    **## ❓ Open questions & assumptions**, force the `needs-human` label when any `[open]` remains,
    and add `open_q=<n>` to the `metrics:` line + REPORT block. Auto ships the question, never an
    invented business answer.
  - **House style (anti-bloat)** — the soft *"precise, pragmatic, brief"* closer on every agent is
    now a concrete rule: *lead with the verdict · tables/bullets over prose · one line per item · no
    preamble, restating, or praise · prose only when a table can't carry the relation.*
  - **Adaptive 🗺 Design block** — the planner now picks the clearest representation per task instead
    of defaulting to mermaid: one line (obvious change) · data-flow table (transforms) · ASCII
    box-flow (topology — and it renders in the PR, mermaid does not since `feature-research/` is
    gitignored) · mermaid reserved for a genuine 2D graph.
  - **Full plan saved in the PR** — both ship paths (`auto` step 8d + gated `approve-diff`) now embed
    the entire reviewed `plan.md` in a `<details>📋 Full plan</details>` collapse. Since
    `feature-research/` is gitignored and the scratch is deleted at ship, the PR body is now the
    plan's only durable home on GitHub — design, blast radius, 🧯 error handling, scorecard,
    decisions, and both reviews travel with the PR.
  - **PR leads with reviewer essentials** — the visible top of the PR is now the actionable stuff:
    **why · what · 🧪 how to test · ⚙️ setup & requirements** (env vars / new deps / config), then
    open questions + the gate stamp. The long-form plan + audit stay in collapses. The implementer's
    `audit.md` gains a `## ⚙️ Setup & test` section that feeds the visible How-to-test + Setup blocks.
- **0.14.0** — **Auto mode: metric references for every new behavior + bigger quote pools.**
  - **Observability** — the `metrics:` line + state.md gained `panel_model`, `arbiter_trigger`, and
    `override`, so each 0.13.0 behavior is greppable (which model the panel ran on, why the arbiter
    fired, which soft guardrails were relaxed; the migration hard-stop surfaces as
    `outcome=ABORTED:needs-migration`). Extended in all three metrics-emit sites + the REPORT block.
  - **More banner quotes** — every persona's quote pool expanded: auto-mode stages 10 → 14, gated
    commands 20 → 24 (IMPLEMENT/DIFF pools kept byte-identical across `approve-plan.md` + `rework.md`;
    each `(M)` label re-synced to its actual count, which the deterministic selector reads).
- **0.13.0** — **Auto mode: operator override policy + tiered diff panel + always-on arbiter.**
  - **Override policy (operator opt-in)** — auto pushes through the *soft* guardrails to finish the
    task (low planner confidence, scope/runaway caps, sensitive non-migration paths now attach a
    `needs-human` heads-up instead of aborting). **Two hard rules never bend:** never authors/applies
    a migration (hard stop + hand-off), never force-pushes any branch but its own `anderson/auto/*`
    (squash-to-clean on its own branch only). The verification engine is unchanged.
  - **Diff panel model is tier-sized (step 7f)** — trivial/normal panels run on sonnet, hard/critical
    on opus (a missed bug at those tiers has real blast radius).
  - **Arbiter backstops every panel (step 7g)** — the opus arbiter now runs on every split **and**
    every unanimous ship (final sign-off, independent re-review — not a rubber-stamp); only a
    unanimous refute skips it. Closes the gap where a panel that agreed too easily could ship a
    subtly-wrong diff. Gate: PASS iff arbiter `ship`; FAIL on arbiter `fix_first` or unanimous refute.
  - **Docs** — full Commands reference + a full auto-mode pipeline section in the root README; the
    "what replaces the human gates" detail, three-modes section, and override policy in this README.
- **0.12.0** — **Auto mode: PR body leads with the validated plan + multi-repo handling.**
  - **PR body restructured (step 8d)** — opens with the source-ticket link (TaskSpec `source_url`,
    rendered only when present — never fabricated) + a short *reviewed-and-validated* plan summary
    (the `## 🛠 How` groups as terse bullets + a one-line gate-validation stamp); the audit trail,
    residual risks, and `metrics:` line collapse into a `<details>` at the bottom.
  - **Multi-repo (steps 2d + 8e)** — when the task must change repos beyond the current one
    (TaskSpec `repos:`, scope outside the repo, or a sibling repo in project memory / `CLAUDE.md`),
    each repo gets an isolated **git worktree**, its own branch off its latest default, and its own
    cross-linked draft PR (`Companion PRs:` ↔ `Part of <task-id>`), labeled `needs-human`.
  - **Worktree isolation** — a dirty working tree is isolated in a worktree instead of aborting, so
    a run never disturbs in-flight work; worktrees are removed on the terminal path.
  - New additive state fields: `source_url`, `repos`. Version bump `0.11.0 → 0.12.0`.
- **0.11.0** — **Auto mode: adaptive verification (panels + routing + arbiter + CI veto).** Wires
  the four `TODO` stubs in `commands/auto.md` into a difficulty-adaptive harness that targets the
  best success-rate / token / latency balance:
  - **Difficulty routing (step 3b)** — a tier (trivial/normal/hard/critical) is derived from the
    plan Scorecard and re-derived from the actual diff size at the gate (max-only; tier can only
    escalate). A forbidden/dependency-path hit pins it to critical.
  - **Plan gate (step 4)** slimmed to criteria-check + one `plan-reviewer` (skipped for trivial) —
    plan errors are cheap, so rigor is spent at the diff gate.
  - **CI veto first (step 7c)** — real GitHub-Actions gate (push branch, await conclusion; in-tree
    fallback). A red build short-circuits before any reviewer tokens are spent.
  - **Tier-sized blind diff panel (step 7f)** — 1/2/3 `reviewer`s by tier
    (correctness · regressions+security · plan-match), run **in parallel** (each writes its own file
    + returns a verdict, so no shared-state collision), blind to `audit.md` and to each other.
  - **Arbiter on split (step 7g)** — unanimous panel decides directly; a split (or critical tier)
    invokes one opus arbiter that rules on merit and must justify it in a required `## Options
    considered` (+/−) table.
  - **Rework (step 7h)** re-enters straight at the panel with a per-round reset; non-convergence
    bounces to PLAN **once** (forced options table) then escalates to `needs-human`.
  - **Red-for-right-reason (step 5)** — a hollow red (import/syntax/collection error) triggers one
    rewrite, else abort.
  - **Calibration metrics** — every run emits a one-line `metrics:` record for later threshold
    tuning.
  Subagents reused unchanged (lens/posture/model passed via the invocation prompt). New additive
  state fields: `plan_panel`, `diff_panel`, `ci_status`, `ci_conclusion`, `red_reason`, `tier`,
  `reviewers`, `arbiter`, `replan_bounced`. Version bump `0.10.0 → 0.11.0`.
- **0.10.0** — **`/anderson:auto` (experimental non-halting mode).** New orchestrator command runs
  the full plan → RED test → implement → diff-review pipeline end-to-end to a draft PR with no human
  halts. Reuses the four existing subagents unchanged. Enforced this increment: baseline-green
  precondition, run lock per task-id, confidence-gate bail-to-human, test-tamper guard (content-hash
  snapshot at RED), scope/forbidden-path guard (`needs-human` label on dependency changes), thrash
  breaker (open-findings must shrink each rework round), draft-PR-only + branch-only ship. Stubbed
  this increment (explicit `TODO` markers): full 3-lens critic/reviewer panels, real CI-runner veto,
  isolated worktree, red-for-right-reason auto-check. Scheduler gains an additive `mode: auto`
  early-exit guard so hook chaining does not interfere. Spec docs moved into plugin:
  `docs/auto-mode.md` + `docs/auto-mode-handoff.md`. Version bump `0.9.7 → 0.10.0`.
- **0.9.7** — Consolidated the human-facing output into ONE document: plan-review and
  diff-review now write into `plan.md` under `## 🔭 Review` (no separate `diff-review.md`),
  and reviewer divergences are inline colored `<del>`/`<ins>` edits at the change site instead
  of a prepended `## Diverged because` block. The planner template gains a `## 🗺 Design` mermaid
  slot and a `###` logical-grouping convention; `state.md` is now machine-only (not a human doc).
  Terminal color added to the shell surfaces — green stages, red gates — in `bin/banner.sh`,
  `bin/demo.sh`, `bin/feature.sh`, `bin/matrix.sh`, all TTY + `NO_COLOR` gated so logs/CI stay clean.
  CI now FAILS a PR that changes `plugins/anderson/` without bumping the version.
- **0.9.6** — Quote pools doubled to 20 per stage and the modulus is now read dynamically
  from the `"Pool (M):"` label in each banner block, so the formula `(N + stageN + iteration) mod M`
  never needs updating when pools grow. All six pools were expanded: the original 10 aphorisms kept
  verbatim plus 10 Matrix-trilogy lines matched to each stage's persona (THE ARCHITECT, THE
  INTERROGATOR, THE ORACLE, NEO, AGENT SMITH, THE ONE). The IMPLEMENT and DIFF_REVIEW pools are
  kept byte-identical across `approve-plan.md` and `rework.md`. Live-loop only; `bin/*` terminal
  scripts unchanged.
- **0.9.5** — Stage banners switched from a model-printed "pick ONE quote at random" instruction
  to a deterministic, model-computable index: `(N + stageN + iteration) mod M`, where N is the
  character count of the task slug, stageN is a fixed offset per stage (PLAN=1, GRILL=2,
  PLAN\_REVIEW=3, IMPLEMENT=4, DIFF\_REVIEW=5, SHIP=6), and iteration is read fresh from
  `state.md`. Varies by task, stage, and rework pass; mod M over the pool always yields a valid
  index. The unreliable tiebreaker ("recall what you already showed") was dropped — iteration
  covers the only recurrence (rework). `rework.md` gained an explicit `iteration += 1` step so
  rework banners read a post-increment value. Live-loop only; 27 scheduler tests pass.
- **0.9.4** — Finished the banner-reliability fix: added a named per-stage **BANNER RULE**
  invariant (setup first, banner last before the agent, nothing between, never skipped)
  restated at every stage so later banners stop getting dropped; `rework.md` now inlines
  the IMPLEMENT 4/5 + DIFF_REVIEW 5/5 banner blocks (was a stale `/4` reference);
  `/anderson:demo` re-synced to the framed `/5` format and now shows the GRILL 2/5 stage.
  Live-loop only; `bin/*` terminal scripts unchanged.
- **0.9.3** — Stage banners now count **/5** (grill is a step — was a stale /4), and each
  banner prints as the last line *before* its agent deploys, so it sits directly above the
  agent's task line instead of scrolling out of view behind setup output.
- **0.9.2** — Richer terminal intro: `bin/matrix.sh` now holds on the ANDERSON logo,
  shows a line, then runs an accelerated montage of a full run (PLAN → … → SHIP with
  the gates). README landing reworked — pipeline + cast + run-walkthrough collapsed into
  one explicit table, a generic quickstart example, the demo GIF up top, **anderson**
  bolded. (Re-record the GIF with `vhs assets/anderson.tape, on the media branch` to capture the new intro.)
- **0.9.1** — Restyled the stage banners into a tight, framed, persona-led format
  (`╭─ ⌐■-■ STAGE · N/4 · PERSONA · model/effort` + a one-line quote) — dropped the
  repeated wordmark + sparkles that made the old 3-line banner feel busy. Statusline
  persona format matched (`PERSONA · model/effort`). Cosmetic only.
- **0.9.0** — Concise, explicit agent output templates (planner `🎯 What / 🤔 Why / 🛠 How /
  ✅ Decisions`; plan- and diff-review `📊 Evaluation / 💬 Feedback / ⚖️ Verdict`) for scannable,
  minimum-words docs with light emoji headers. New `regrill` plan-review verdict that
  auto-routes `plan_review → grill` (human-gated, resets the verdict to avoid re-bounce).
  `scheduler.py` refactored to an importable `main()` with a 27-test stdlib `unittest` suite.
  Added `LICENSE` (MIT) + README badges/hook/quickstart/persona table. Dogfooded through
  anderson's own pipeline. Agent model/effort unchanged.
- **0.8.1** — Headless parity for ship: `bin/feature.sh --approve-diff` now branches
  (off the default branch, `anderson/<slug>`), commits, pushes, and opens the PR — the
  same guarded flow as the interactive command, but with the commit subject + PR body
  built deterministically from the scratch (no model). Sets a CI fallback git identity
  only if none exists; handles detached HEAD; degrades gracefully without a remote / `gh`.
- **0.8.0** — New **grill** step between plan and plan-review. After the planner drafts
  `plan.md`, anderson interviews you relentlessly about it — one question at a time, down
  each branch of the decision tree, recommending an answer to each, exploring the codebase
  instead of asking when it can — and folds every resolved decision into `plan.md` (under
  `## Decisions`), so the reviewer critiques a hardened plan. Self-contained (no external
  skill); inlined into `/anderson:start`. The scheduler halts at grill as a human checkpoint
  and never auto-skips it. Agent model/effort settings unchanged.
- **0.7.0** — `/anderson:approve-diff` now **ships for real**: it commits the work
  cleanly on a branch (auto-creates `anderson/<slug>` when you're on the default branch,
  else commits on the current branch), pushes, and opens a PR with a generated
  description. Fully guarded — degrades to commit-only + printed PR body when there's no
  remote / no `gh` / not authed; never force-pushes; runs in any repo. Previously it only
  handed you the message. Loop logic + agent model/effort settings unchanged.
- **0.6.3** — Quote pools grew 4 → 10 per stage, with a stronger "pick at random,
  don't reuse one shown this session" instruction so banners stop repeating. The SHIP
  banner gets a dedicated 10-quote ending pool, and the DONE line now states the loop
  has fully stopped (nothing runs in the background). Cosmetic + UX; loop logic unchanged.
- **0.6.2** — Statusline glasses now cycle **colour** each refresh (green → bright
  green → bright cyan → cyan) — closest a plugin can get to a live, "tinkering…"-style
  colour shimmer (refresh-paced, not smooth). Statusline only; honors `NO_COLOR`; loop unchanged.
- **0.6.1** — Stage banners get a glitter accent (`✦` framing the glasses), and the
  GATE prompts now print the resolved command with the real feature slug filled in
  (`/anderson:approve-plan brief-views`, copy-pasteable) instead of a literal `<task>`.
  Cosmetic + UX only; loop logic unchanged. (In-chat banners stay static — true motion
  lives in `bin/statusline.sh` / `bin/matrix.sh`.)
- **0.6.0** — Terminal `bin/matrix.sh` intro (digital rain → glasses/title) and an opt-in
  one-line `bin/statusline.sh` shimmer showing the live stage. Extras only; the loop is unchanged.
- **0.5.1** — Banners render as inline command text (no plugin-script execution), so
  they work for any user without a bash-permission grant; `bin/banner.sh` / `bin/demo.sh` stay for terminal use.
- **0.5.0** — Matrix-flavored stage banners (sunglasses sigil + rotating original,
  mood-matched aphorisms) and a zero-token `/anderson:demo` dry-run of the full pipeline.
- **0.4.0** — Autonomous chaining now actually drives the next turn: the scheduler
  emits real `Stop`/`SubagentStop` hook JSON (`decision:block`+`reason` to chain,
  allow-stop `additionalContext` at gates) instead of discarded stdout, with a
  `stop_hook_active` re-entrancy guard. State parsing is lenient (tolerates `- `
  bullets / `**` bold), and the interactive `/anderson:start` command seeds the exact
  machine-readable STATE block so `/anderson:status` and the scheduler stay in sync.
- **0.3.1** — Gated 4-stage pipeline with per-stage model/effort and two human gates.

Licensed under the [MIT License](LICENSE).
