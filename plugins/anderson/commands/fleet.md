---
description: "THE OPERATOR: install the `fleet` command (cross-repo monitor of every Claude session: persona, stage, $, ctx) and show how to launch it. Idempotent."
allowed-tools: Bash(bash:*)
---
Install result (writes a stable `fleet` shim to ~/.local/bin; safe to re-run):
!`bash "${CLAUDE_PLUGIN_ROOT}/bin/fleet" install 2>&1`

Print the card below exactly as written, then the install result above verbatim under a
`setup:` line (it may include a PATH line and a tmux hotkey line; both are copy-paste ready).
No other tools, no commentary before or after. The monitor runs OUTSIDE Claude (plain python
curses, zero tokens); this command only installs the launcher and tells the human how to start it.

```
⌐■-■  THE OPERATOR — every Claude Code session on this machine, one row each

  launch:   fleet                 right here, in the current terminal (tmux or not)
            fleet --tmux          outside tmux: a persistent tmux session "fleet", status bar hidden
            fleet --pane          in tmux: 45% side pane        fleet --window   in tmux: new window
            fleet --demo          four fake rows to try the UI   fleet --once     one plain frame
            fleet --theme zion    matrix · construct · zion · nebuchadnezzar · agent (saved)
            fleet --plain         plain header wording (saved)  fleet --calm     no motion (saved)
            fleet --zoom 16       Terminal.app: bigger font while fleet runs, restored on quit (saved)

  header:   matrix · session ▓▓▓▓░░░░░░ 42% · 3h39 left │ week ▓▓▓▓▓░░░░░ 52% · resets Fri 19:00
            (the /usage windows, red past 90%: your plan is a flat fee, these percentages are the
            cost; the api$ estimate is hidden, `$` or --cost shows it in the footer)

  row:      flags · repo · task · persona · stage n/max · model · now · ctx · age
            ☎ waits on you   ▶ working   ✝ process gone   ⟲ rework loop
            ▲ ARCHITECT · ◇ INTERROGATOR · ◎ ORACLE · ● NEO · ▣ AGENT SMITH · ★ THE ONE · ○ no pipeline

  keys:     ↑↓ tune · 1-9 / ⏎ jack in · w oldest waiting · r kill (asks; hides the row) · b hide row · h show hidden
            c copy `claude --resume` for the row · n desktop notification on ring (skipped, with the
              sound, when that session's terminal is already frontmost; fleet --ping tests the banner)
            m sound on/off · s next ring sound (phone · snare · hitech · freeze · blip · rift · jump;
              fleet --play all auditions them, --ring NAME picks, own .wav in ~/.claude/fleet/sounds/)
            o read plan.md / audit.md right here (glow, else less; q returns)
            O open them in your IDE (automatic when ⏎ lands on a human gate and an IDE applies;
              editor: --editor code, else GUI $VISUAL/$EDITOR, else the IDE owning the session)
            / filter · t theme · p wording · +/- zoom (Terminal.app; iTerm2/IDE: ⌘+) · ? manual · q

  card:     task · who · verdicts · status · context · agents (subagents sent / running / last) · where
            · prompt · last · next; footer pinned to the floor: keys line, then usage line

  jack in:  ⏎ switches tmux to the session's pane. No tmux? On macOS it focuses the iTerm2 /
            Terminal.app tab that owns the session, or brings the owning IDE forward for
            integrated terminals (WebStorm, VS Code, Cursor). tmux is optional:
            fleet install --with-tmux adds it (brew / apt / dnf) if you want panes.

  data:     found with no setup (ps + transcripts + state.md). This plugin's hooks add the exact
            waiting/working signal. $ and precise ctx need the statusline heartbeat: use
            bin/statusline.sh, or keep yours and wrap it in settings.json:
              "statusLine": { "type": "command",
                "command": "bash $ROOT/bin/fleet-statusline.sh bash /ABS/PATH/your-statusline.sh" }
```
