# fleet-operator.tape — the live fleet board (THE OPERATOR), as a still.
#
#   install once:  brew install vhs        # https://github.com/charmbracelet/vhs
#   record:        vhs assets/fleet-operator.tape   ->   assets/fleet-operator.png
#
# Wide enough for every column (model · now · ctx · age) and tall enough for the
# labelled detail card. --demo fills the board with fake rows plus any live session.

Output assets/fleet-operator.gif

Set Shell "bash"
Set FontSize 17
Set Width 1760
Set Height 640
Set Padding 24
Set TypingSpeed 0

Hide
Type "clear; python3 plugins/anderson/bin/fleet.py --demo --no-intro"
Enter
Show
Sleep 2s
Screenshot assets/fleet-operator.png
