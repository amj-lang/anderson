# fleet-loading.tape — the digital-rain "Loading anderson…" boot screen, as a still.
#
#   install once:  brew install vhs        # https://github.com/charmbracelet/vhs
#   record:        vhs assets/fleet-loading.tape   ->   assets/fleet-loading.png
#
# Run from the repo root. VHS runs the command in a real pty, so curses draws for real.
# Writing boot_n pins the rotating boot line, so the still is reproducible.

Output assets/fleet-loading.gif

Set Shell "bash"
Set FontSize 20
Set Width 1200
Set Height 700
Set Padding 24
Set TypingSpeed 0

Hide
Type "printf 0 > ~/.claude/fleet/boot_n; clear; python3 plugins/anderson/bin/fleet.py --demo"
Enter
Show
Sleep 700ms
Screenshot assets/fleet-loading.png
