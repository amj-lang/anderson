#!/usr/bin/env bash
# anderson — terminal intro: digital rain → glasses/title (held) → a line →
# an accelerated montage of one full run. Pure flair. Run in a REAL terminal:
#   bash bin/matrix.sh
# Safe everywhere: non-TTY / TERM=dumb / NO_COLOR / --still → one static frame.
# Tunables: MATRIX_DELAY (0.06), MATRIX_FRAMES (30), MATRIX_HOLD (1.4s on logo),
#           MATRIX_MONTAGE_DELAY (0.5s per stage).
set -euo pipefail

still=0
[ "${1:-}" = "--still" ] && still=1

tty=1
[ -t 1 ] || tty=0
case "${TERM:-}" in dumb|"") tty=0 ;; esac

color=1
if [ -n "${NO_COLOR:-}" ] || [ "$tty" -eq 0 ]; then color=0; fi

grn(){  if [ "$color" -eq 1 ]; then printf '\033[32m';   fi; }
grnb(){ if [ "$color" -eq 1 ]; then printf '\033[1;32m'; fi; }
rst(){  if [ "$color" -eq 1 ]; then printf '\033[0m';    fi; }

quotes=(
  "the agents review the agents"
  "green is not understood — read what you merged"
  "two gates, because nothing merges unseen"
  "plan twice, so reality only happens once"
  "the loop ends where your judgement begins"
)
QUOTE="${quotes[$(( RANDOM % ${#quotes[@]} ))]}"

logo(){
  printf '\n\n'
  grnb; printf '            ⌐■-■   A N D E R S O N\n'; rst
  printf '\n'
  grn;  printf '            gated maker/checker loop\n'; rst
  printf '\n'
}

# Accelerated montage of one run: each stage flashes in with its persona + gate.
montage(){
  local d="${MATRIX_MONTAGE_DELAY:-0.5}"
  printf '\033[2J\033[H\n'
  grnb; printf '   ⌐■-■  A N D E R S O N    ·    one task → a reviewed, shipped PR\n\n'; rst
  step(){ grnb; printf '   ▸ %-12s' "$1"; rst; grn; printf ' %s\n' "$2"; rst; sleep "$d"; }
  step "PLAN"        "THE ARCHITECT · opus/high"
  step "GRILL"       "THE INTERROGATOR · you"
  step "PLAN_REVIEW" "THE ORACLE · opus/xhigh        ■ GATE 1"
  step "IMPLEMENT"   "NEO · sonnet/medium"
  step "DIFF_REVIEW" "AGENT SMITH · opus/xhigh       ■ GATE 2"
  step "SHIP ✓"      "THE ONE · commit + PR"
  printf '\n'; sleep 1.2
}

# Static fallback (non-TTY / dumb / NO_COLOR / --still): logo + line, no animation.
if [ "$tty" -eq 0 ] || [ "$still" -eq 1 ]; then
  logo
  grn; printf '            "%s"\n\n' "$QUOTE"; rst
  exit 0
fi

cols=$(tput cols 2>/dev/null || echo 80)
lines=$(tput lines 2>/dev/null || echo 24)
[ "$cols" -gt 100 ] && cols=100
[ "$lines" -gt 18 ] && lines=18

cleanup(){ rst; printf '\033[?25h\033[2J\033[H'; }
trap cleanup EXIT INT TERM
printf '\033[?25l\033[2J'

delay="${MATRIX_DELAY:-0.06}"
frames="${MATRIX_FRAMES:-30}"
hold="${MATRIX_HOLD:-1.4}"

f=0
while [ "$f" -lt "$frames" ]; do
  printf '\033[H'
  grn
  awk -v cols="$cols" -v lines="$lines" -v seed="$(( RANDOM * (f + 1) + RANDOM ))" '
    BEGIN{ srand(seed); CH="01101001#%&*+=|/!?.:"; n=length(CH);
      for (r=0; r<lines; r++){ s="";
        for (c=0; c<cols; c++){ s = s (rand() < 0.20 ? substr(CH, int(rand()*n)+1, 1) : " ") }
        print s } }'
  rst
  sleep "$delay"
  f=$(( f + 1 ))
done

# Resolve the rain into the logo, hold on it, then show a line.
printf '\033[2J\033[H'
pad=$(( lines / 2 - 3 )); i=0
while [ "$i" -lt "$pad" ]; do printf '\n'; i=$(( i + 1 )); done
logo
sleep "$hold"
grn; printf '            "%s"\n' "$QUOTE"; rst
sleep 1.6

# Then the accelerated run.
montage
