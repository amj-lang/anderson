#!/usr/bin/env bash
# anderson — terminal "digital rain" intro that resolves into the glasses + title.
# Pure flair. Run it in a REAL terminal:   bash bin/matrix.sh
# Safe everywhere: if stdout is not a TTY, or TERM=dumb, or NO_COLOR is set, it
# prints one static frame (no escape codes, no animation) and exits.
# Tunables: MATRIX_DELAY (default 0.07s/frame), MATRIX_FRAMES (default 24).
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

logo(){
  printf '\n\n'
  grnb; printf '            ⌐■-■   A N D E R S O N\n'; rst
  printf '\n'
  grn;  printf '            gated maker/checker loop — the agents review the agents\n'; rst
  printf '\n'
}

# Static fallback (non-TTY / dumb term / NO_COLOR / --still): no animation.
if [ "$tty" -eq 0 ] || [ "$still" -eq 1 ]; then
  logo
  exit 0
fi

cols=$(tput cols 2>/dev/null || echo 80)
lines=$(tput lines 2>/dev/null || echo 24)
[ "$cols" -gt 100 ] && cols=100
[ "$lines" -gt 18 ] && lines=18

cleanup(){ rst; printf '\033[?25h\033[2J\033[H'; }
trap cleanup EXIT INT TERM
printf '\033[?25l\033[2J'

delay="${MATRIX_DELAY:-0.07}"
frames="${MATRIX_FRAMES:-24}"

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

# Resolve the rain into the logo.
printf '\033[2J\033[H'
pad=$(( lines / 2 - 2 )); i=0
while [ "$i" -lt "$pad" ]; do printf '\n'; i=$(( i + 1 )); done
logo
sleep 0.5
