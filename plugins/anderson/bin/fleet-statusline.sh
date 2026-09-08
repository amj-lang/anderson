#!/usr/bin/env bash
# fleet-statusline — keep YOUR statusline, add the fleet heartbeat. Wraps any statusline
# command: the session JSON is copied to bin/heartbeat.py, then handed unchanged to the
# inner command, whose output is the status bar. Wire it in settings.json:
#   "statusLine": { "type": "command",
#     "command": "bash /ABS/PATH/plugins/anderson/bin/fleet-statusline.sh bash /ABS/PATH/your-statusline.sh" }
# With no inner command it prints nothing (heartbeat only).
set -uo pipefail
_in="$(cat 2>/dev/null || true)"
_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -n "$_in" ] && { printf '%s' "$_in" | FLEET_PID=$PPID python3 "$_dir/heartbeat.py" >/dev/null 2>&1 & }
[ "$#" -gt 0 ] && printf '%s' "$_in" | "$@"
exit 0
