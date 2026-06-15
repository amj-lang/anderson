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

printf '\n  D E M O   M O D E   ·   no agents · no tokens · instant\n'
printf '  every banner and gate below is exactly what a real run prints\n\n'
rule; pause

bash "$banner" plan
printf '        · planner reads the repo and writes plan.md\n\n'; pause
bash "$banner" plan_review
printf '        · plan-reviewer rewrites plan.md, prepends "## Diverged because"\n\n'; pause

rule
printf '  ■ GATE 1 · your turn. Read plan.md (## Diverged because, verdict=ship).\n'
printf '    Approve: /anderson:approve-plan demo-task   (or just say "approved, go")\n'
rule; pause

bash "$banner" implement
printf '        · implementer executes plan.md and writes audit.md\n\n'; pause
bash "$banner" diff_review
printf '        · reviewer diffs the scope and writes diff-review.md\n\n'; pause

rule
printf '  ■ GATE 2 · awaiting you. Read diff-review.md AND the diff (verdict=ship).\n'
printf '    Ship: /anderson:approve-diff demo-task    Rework: /anderson:rework demo-task\n'
rule; pause

bash "$banner" ship
printf '        · hands you a commit message, removes the scratch dir\n\n'
printf '  demo complete — a real run differs only in that the four agents actually think.\n\n'
