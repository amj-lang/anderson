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

  launch:   fleet                 in tmux: this pane · outside: opens tmux session "fleet" · no tmux: plain
            fleet --pane          in tmux: 45% side pane        fleet --window   in tmux: new window
            fleet --here          current terminal, never touches tmux
            fleet --demo          four fake rows to try the UI   fleet --once     one plain frame
            fleet --theme zion    matrix · construct · zion · nebuchadnezzar · agent (saved)
            fleet --plain         plain header wording (saved)  fleet --calm     no motion (saved)

  row:      flags · repo · task · persona · stage n/max · model · now · $ · ctx · age
            ☎ waits on you   ▶ working   ✝ process gone   ⟲ rework loop
            ▲ ARCHITECT · ◇ INTERROGATOR · ◎ ORACLE · ● NEO · ▣ AGENT SMITH · ★ THE ONE · ○ no pipeline

  keys:     ↑↓ tune · ⏎ jack in · w oldest waiting · r kill (asks) · b dismiss dead
            / filter · t theme · p wording · ? manual · q

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
