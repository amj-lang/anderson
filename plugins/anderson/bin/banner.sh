#!/usr/bin/env bash
# anderson banner — sunglasses sigil + a random, mood-matched line.
# Usage: banner.sh <stage>     stage = plan | plan_review | implement | diff_review | ship
# Lines (bin/quotes.txt) are tagged by mood; each stage draws from its mood bucket,
# falling back to any line. Lines are original aphorisms (no third-party text).
set -euo pipefail

stage="${1:-plan}"
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
quotes="$dir/quotes.txt"

tty=1
[ -t 1 ] || tty=0
case "${TERM:-}" in dumb|"") tty=0 ;; esac
color=1
if [ -n "${NO_COLOR:-}" ] || [ "$tty" -eq 0 ]; then color=0; fi
grn(){  if [ "$color" -eq 1 ]; then printf '\033[32m';   fi; }
grnb(){ if [ "$color" -eq 1 ]; then printf '\033[1;32m'; fi; }
rst(){  if [ "$color" -eq 1 ]; then printf '\033[0m';    fi; }

case "$stage" in
  plan)        persona="THE ARCHITECT"; agent="planner";       spec="opus · high";     act="scoping → plan.md";         n="1/4"; mood="design";;
  plan_review) persona="THE ORACLE";    agent="plan-reviewer";  spec="opus · xhigh";    act="editing plan.md";           n="2/4"; mood="insight";;
  implement)   persona="NEO";           agent="implementer";    spec="sonnet · medium"; act="executing plan.md";         n="3/4"; mood="action";;
  diff_review) persona="AGENT SMITH";   agent="reviewer";       spec="opus · xhigh";    act="read-only diff review";     n="4/4"; mood="adversary";;
  ship|done)   persona="THE ONE";       agent="";               spec="";                act="welcome to the real world"; n="✓";   mood="mentor";;
  *)           persona="ANDERSON";      agent="$stage";         spec="";                act="";                          n="•";   mood="";;
esac

quote=""
if [ -f "$quotes" ]; then
  pool=""
  [ -n "$mood" ] && pool="$(grep -i "^${mood}|" "$quotes" || true)"
  [ -z "$pool" ] && pool="$(cat "$quotes")"
  line="$(printf '%s\n' "$pool" | awk -v seed="$RANDOM$$" 'BEGIN{srand(seed)} NF{a[++n]=$0} END{if(n)print a[int(rand()*n)+1]}')"
  quote="${line#*|}"
fi

mid="$persona"
[ -n "$agent" ] && mid="$mid · $agent"
[ -n "$spec" ]  && mid="$mid · $spec"
[ -n "$act" ]   && mid="$mid · $act"

grn; printf '  ⌐■-■  A N D E R S O N   ·   %s · %s\n' "$n" "$(printf '%s' "$stage" | tr 'a-z' 'A-Z')"; rst
printf '        %s\n' "$mid"
[ -n "$quote" ] && printf '        "%s"\n' "$quote"
