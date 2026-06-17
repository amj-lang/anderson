# anderson.tape — render the digital-rain intro to a GIF with VHS.
#
#   install once:  brew install vhs        # https://github.com/charmbracelet/vhs
#   record:        vhs assets/anderson.tape    ->    assets/anderson-demo.gif
#
# Run from the repo root. VHS runs the command in a real pty, so matrix.sh
# animates (not the static fallback). Tweak FontSize/Width/Height/frames to taste.

Output assets/anderson-demo.gif

Set Shell "bash"
Set FontSize 20
Set Width 1000
Set Height 560
Set Padding 20
Set TypingSpeed 0

# Type the command hidden, then reveal during the animation.
Hide
Type "MATRIX_FRAMES=30 MATRIX_DELAY=0.06 bash plugins/anderson/bin/matrix.sh"
Enter
Show
Sleep 12s
