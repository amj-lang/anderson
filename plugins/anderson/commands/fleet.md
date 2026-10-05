---
description: "THE OPERATOR: install the `fleet` command (cross-repo monitor of every Claude session: persona, stage, $, ctx) and show how to launch it. Idempotent."
allowed-tools: Bash(bash:*)
---
Install result (writes a stable `fleet` shim to ~/.local/bin; safe to re-run):
!`bash "${CLAUDE_PLUGIN_ROOT}/bin/fleet" install $ARGUMENTS 2>&1`

Print the card below exactly as written, then the install result above verbatim under a
`setup:` line (it may include a PATH line, an `extras:` report of optional tools with their install
lines, and a tmux hotkey line; all copy-paste ready).
No other tools, no commentary before or after. The monitor runs OUTSIDE Claude (plain python
curses, zero tokens); this command only installs the launcher and tells the human how to start it.

```
⌐■-■  THE OPERATOR — every Claude Code session on this machine, one row each

  launch:   fleet                 right here, in this terminal tab
            fleet --focus         bring the running fleet's tab back to the front (bind it to a hotkey)
            fleet --tmux          a tmux session "fleet"   ·   --pane / --window inside tmux
            fleet --once          one plain frame
            fleet --plain · --calm · --cost · --notify · --ring NAME (all saved)

  update:   fleet update          fetch the newest anderson, then restart Claude Code

  screen:   top: every live session, ringing first; closed / long-dead ones fold into one `dead` line.
            below: the workspace's repos, where N starts work (the new agent is selected once it appears)
  row:      flags · repo · task (Claude's session title) · pipeline (persona · stage n/max · tier) · now · ctx · age
            ☎ waits on you (turn done, permission, question)   ▶ working   ✝ process gone   ⟲ rework loop
  rings:    once, 5 s after a session starts waiting, never while its own tab is in front of you

  keys:     ↑↓ tune · ⏎/1-9 jack in (dead session: resume it in a new tab; repo: spawn box)
            N new agent (p bare · a /anderson:start · A /anderson:auto; a repo on a feature branch
              gets a worktree, so its work in progress is never touched)
            w longest-waiting ring · o read plan / audit / diff · r kill · b hide · h hidden
            space fold the repos or the dead line · m sound on/off (every fleet at once) · / filter · ? manual · q

  jack in:  finds the session's tab in the app that owns it: Ghostty (exact, by tty), iTerm2,
            Terminal.app, a tmux pane, or the IDE. With --notify + terminal-notifier, clicking a
            ring banner jumps there too.

  extras:   python3 is all it needs. Optional: glow (o renders markdown), terminal-notifier (macOS
            banners), tmux. `/anderson:fleet --extras` installs the first two, `--with-tmux` the third.

  data:     found with no setup (ps + transcripts + state.md). This plugin's hooks add the exact
            waiting/working signal. ctx and /usage need the statusline heartbeat: use
            bin/statusline.sh, or keep yours and wrap it in settings.json:
              "statusLine": { "type": "command",
                "command": "bash $ROOT/bin/fleet-statusline.sh bash /ABS/PATH/your-statusline.sh" }
```
