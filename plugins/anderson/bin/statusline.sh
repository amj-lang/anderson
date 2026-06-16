#!/usr/bin/env bash
# anderson statusline — one compact line: live loop stage + a calm shimmer
# (glasses lens + colour + rain tail cycle ~once/second). Wire it in settings.json:
#   "statusLine": { "type": "command", "command": "bash /ABS/PATH/bin/statusline.sh" }
# Reads the most-recent feature-research/*/state.md in the current repo (if any).
set -euo pipefail
_in="$(cat 2>/dev/null || true)"      # drain the session JSON on stdin (unused)

fr=$(( $(date +%s) % 4 ))             # shimmer frame, advances ~1/second

G=""; R=""; eyecols=("" "" "" "")
if [ -z "${NO_COLOR:-}" ]; then
  G=$'\033[32m'; R=$'\033[0m'
  # glasses colour rotates each refresh: green, bright green, bright cyan, cyan
  eyecols=($'\033[32m' $'\033[1;32m' $'\033[1;36m' $'\033[36m')
fi
ec="${eyecols[$fr]}"

case "$fr" in
  0) eyes="⌐■-■" ;;
  1) eyes="⌐▪-▪" ;;
  2) eyes="⌐•-•" ;;
  *) eyes="⌐▪-▪" ;;
esac
rains=("0·1 1" "1 0·1" " 1·10" "1·0 1")
rain="${rains[$fr]}"

field(){ grep -iE "^[[:space:]]*(-[[:space:]]+)?\**$1\**[[:space:]]*:" "$2" 2>/dev/null | head -1 | sed -E 's/^[^:]*:[[:space:]]*//; s/[[:space:]]*\**[[:space:]]*(#.*)?$//' || true; }

st="$(ls -t feature-research/*/state.md 2>/dev/null | head -1 || true)"
if [ -n "$st" ] && [ -f "$st" ]; then
  stage="$(field stage "$st")"
  task="$(field task "$st")"
  case "$stage" in
    plan)        who="THE ARCHITECT opus/high" ;;
    grill)       who="THE INTERROGATOR · you" ;;
    plan_review) who="THE ORACLE opus/xhigh" ;;
    implement)   who="NEO sonnet/medium" ;;
    diff_review) who="AGENT SMITH opus/xhigh" ;;
    done)        who="shipped" ;;
    *)           who="${stage:-?}" ;;
  esac
  mid="${task%% *} · ${stage:-?} · ${who}"
else
  mid="idle · /anderson:start to begin"
fi

printf '%s%s%s %sanderson%s · %s · %s%s%s\n' "$ec" "$eyes" "$R" "$G" "$R" "$mid" "$G" "$rain" "$R"
