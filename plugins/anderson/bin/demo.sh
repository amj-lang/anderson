#!/usr/bin/env bash
# anderson demo — walk the whole pipeline UX (every banner + both gates) with
# NO agents, NO tokens, no waiting. A pure-local preview of a real run.
# Usage: bash bin/demo.sh          (set DEMO_DELAY=0 for instant; default 0.4s)
set -euo pipefail
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
banner="$dir/banner.sh"
delay="${DEMO_DELAY:-0.4}"
pause(){ if [ "$delay" != "0" ]; then sleep "$delay"; fi; }
rule(){ printf '  ────────────────────────────────────────────────────────────\n'; }

tty=1
[ -t 1 ] || tty=0
case "${TERM:-}" in dumb|"") tty=0 ;; esac
color=1
if [ -n "${NO_COLOR:-}" ] || [ "$tty" -eq 0 ]; then color=0; fi
red(){  if [ "$color" -eq 1 ]; then printf '\033[31m'; fi; }
rst(){  if [ "$color" -eq 1 ]; then printf '\033[0m';  fi; }

printf '\n  D E M O   M O D E   ·   no agents · no tokens · instant\n'
printf '  every banner and gate below is exactly what a real run prints\n\n'
rule; pause

bash "$banner" plan
printf '        · planner reads the repo and writes plan.md\n\n'; pause
bash "$banner" plan_review
printf '        · plan-reviewer makes inline strike-through edits + writes its review under ## 🔭 Review\n\n'; pause

rule
red; printf '  ■ GATE 1 · your turn. Read plan.md (## 🔭 Review, verdict=ship).\n'; rst
printf '    Approve: /anderson:approve-plan demo-task   (or just say "approved, go")\n'
rule; pause

bash "$banner" implement
printf '        · implementer executes plan.md and writes audit.md\n\n'; pause
bash "$banner" diff_review
printf '        · reviewer diffs the scope and appends its diff review under plan.md ## 🔭 Review\n\n'; pause

rule
red; printf '  ■ GATE 2 · awaiting you. Read plan.md ## 🔭 Review AND the diff (verdict=ship).\n'; rst
printf '    Ship: /anderson:approve-diff demo-task    Rework: /anderson:rework demo-task\n'
rule; pause

bash "$banner" ship
printf '        · hands you a commit message, removes the scratch dir\n\n'
printf '  demo complete — a real run differs only in that the four agents actually think.\n\n'
