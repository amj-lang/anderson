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

  launch:   fleet                 outside tmux: attaches a per-workspace tmux session (status bar
                                  on); inside tmux: right here in the current window
            fleet --here          run right here regardless of tmux
            fleet --tmux          outside tmux: the legacy persistent session "fleet", status bar hidden
            fleet --pane          in tmux: 45% side pane        fleet --window   in tmux: new window
            fleet --demo          four fake rows to try the UI   fleet --once     one plain frame
            fleet --theme zion    matrix · construct · zion · nebuchadnezzar · agent (saved)
            fleet --plain         plain header wording (saved)  fleet --calm     no motion (saved)
            fleet --zoom 16       Terminal.app: bigger font while fleet runs, restored on quit (saved)

  update:   fleet update          fetch the newest anderson (marketplace refresh + plugin update),
                                  then restart Claude Code. The ~/.local/bin shim resolves the
                                  newest cached version at run time, so no re-install needed.

  header:   matrix · session ▓▓▓▓░░░░░░ 42% · 3h39 left │ week ▓▓▓▓▓░░░░░ 52% · resets Fri 19:00
            (the /usage windows, red past 90%: your plan is a flat fee, these percentages are the
            cost; the api$ estimate is hidden, `$` or --cost shows it in the footer)

  tree:     rows are the repos of the workspace fleet was launched from, one nested level: a repo
            holding a rework loop is a row, a dir holding several repos is a collapsible group row,
            live sessions nest under their repo, and sessions from elsewhere land in an `elsewhere`
            group. `J`/`K` reorder a repo/group among its siblings, `space` (or `←`/`→`) collapses
            it; both persist per workspace. No repos found under the launch dir -> today's flat list.

  row:      flags · repo · task · persona · stage n/max · model · now · ctx · age
            ☎ waits on you   ▶ working   ✝ process gone   ⟲ rework loop
            ▲ ARCHITECT · ◇ INTERROGATOR · ◎ ORACLE · ● NEO · ▣ AGENT SMITH · ★ THE ONE · ○ no pipeline

  keys:     ↑↓ tune · 1-9 / ⏎ jack in (session row) or spawn an agent (repo/group row) · J/K reorder
              a repo/group · space collapse/expand (←/→ too) · D pop a session's window out into
              its own terminal · w oldest waiting · r kill (asks; hides the row) · b hide row, or a whole repo · h show hidden
            ⏎ on a sentinel revives it in a new terminal · ⏎ on a repo/group row opens a prompt box,
              then p/a/A spawns a claude agent (bare / /anderson:start / /anderson:auto) into that
              repo — or the workspace root, on a group — in a terminal of its own; fleet keeps the
              window it is in, the agent never takes it over. Repo already on a feature branch? the
              agent gets a worktree there (`.worktrees/<task>`, branch `anderson/<task>`, off the
              default branch), so the work in progress sitting in that checkout is never touched
            c copy `claude --resume` · n desktop notification on ring (skipped, with the
              sound, when that session's terminal is already frontmost; fleet --ping tests the banner)
            m sound on/off · s next ring sound (phone · snare · hitech · freeze · blip · rift · jump;
              fleet --play all auditions them, --ring NAME picks, own .wav in ~/.claude/fleet/sounds/)
            o read plan.md / audit.md right here (glow, else less; q returns)
            a page the newest subagent's transcript as a readable log (running ones first)
            O open them in your IDE (automatic when ⏎ lands on a human gate and an IDE applies;
              editor: --editor code, else GUI $VISUAL/$EDITOR, else the IDE owning the session)
            / filter · t theme · p wording · +/- zoom (Terminal.app; iTerm2/IDE: ⌘+) · ? manual · q

  card:     task · who · verdicts · status · context · agents (sent / running, then one live line per
            running subagent: type, task, current tool, age) · where
            · prompt · last · next; footer pinned to the floor: keys line, then usage line

  jack in:  ⏎ switches tmux to the session's pane. No tmux? On macOS it focuses the iTerm2 /
            Terminal.app tab that owns the session, or brings the owning IDE forward for
            integrated terminals (WebStorm, VS Code, Cursor). tmux is optional:
            fleet install --with-tmux adds it (brew / apt / dnf) if you want panes.

  extras:   python3 + what the OS has is all it needs. Optional: glow (o renders markdown),
            terminal-notifier (macOS banners), tmux. `/anderson:fleet --extras` installs the
            first two, `--with-tmux` the third, `--all` everything; the setup line says which are missing.

  data:     found with no setup (ps + transcripts + state.md). This plugin's hooks add the exact
            waiting/working signal. $ and precise ctx need the statusline heartbeat: use
            bin/statusline.sh, or keep yours and wrap it in settings.json:
              "statusLine": { "type": "command",
                "command": "bash $ROOT/bin/fleet-statusline.sh bash /ABS/PATH/your-statusline.sh" }
```
