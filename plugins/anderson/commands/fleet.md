---
description: "THE OPERATOR: how to launch the cross-repo fleet monitor (every Claude session, persona, stage, $, ctx) in a tmux pane. Static card, reads nothing."
allowed-tools: Bash(echo:*)
---
Plugin root on this machine: !`echo "${CLAUDE_PLUGIN_ROOT:-<unset>}"`

Print the card below exactly as written, substituting the plugin root above for
`$ROOT` — no tools beyond that, no additions, no commentary before or after. The monitor
runs OUTSIDE Claude (a plain python curses program, zero tokens); this command only tells
the human how to start it.

```
⌐■-■  THE OPERATOR — every Claude Code session on this machine, one row each

  launch (in its own tmux pane, so ⏎ can jack into the others):
    python3 $ROOT/bin/fleet.py               live · --demo adds 4 fake rows · --no-intro · --ascii
    python3 $ROOT/bin/fleet.py --once        one plain-text frame (scripts, non-TTY)

  row:   flags · repo · task · persona · stage n/max · model · now · $ · ctx · age
         ☎ ring = waits on you   ▶ = working   ✝ sentinel = process gone   ⟲ = déjà vu (rework loop)
         persona from feature-research/*/state.md: ▲ ARCHITECT · ◇ INTERROGATOR · ◎ ORACLE · ● NEO
         ▣ AGENT SMITH · ★ THE ONE · ○ T. ANDERSON (session with no pipeline yet)

  keys:  ↑↓ tune · ⏎ jack in · w white rabbit (oldest ring) · r red pill (kill, asks)
         b blue pill (dismiss sentinel) · / filter · t theme · p wording · ? manual · q

  look:  themes matrix · construct · zion · nebuchadnezzar · agent (t cycles, --theme sets);
         p or --plain = plain header wording; --calm = no motion. All saved in ~/.claude/fleet/prefs.json.

  data:  sessions are found with no setup (ps + transcripts). Hooks in this plugin add the exact
         waiting/working signal. $ and precise ctx need the statusline heartbeat — either use
         bin/statusline.sh, or keep yours and wrap it:
           "statusLine": { "type": "command",
             "command": "bash $ROOT/bin/fleet-statusline.sh bash /ABS/PATH/your-statusline.sh" }
```
