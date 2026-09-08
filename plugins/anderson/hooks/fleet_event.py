#!/usr/bin/env python3
"""
fleet event hook — records the last lifecycle event of a Claude Code session in
~/.claude/fleet/<session_id>.event.json so bin/fleet.py (THE OPERATOR) can tell
"waiting on you" (Stop / Notification) from "working" (UserPromptSubmit / PostToolUse)
without guessing from the transcript. Wired for SessionStart, UserPromptSubmit,
PostToolUse, Notification, Stop, SessionEnd in hooks/hooks.json.

Emits nothing on stdout: this hook never steers the session. Never raises.
"""
import json, os, sys, time

FLEET_DIR = os.path.expanduser(os.environ.get("ANDERSON_FLEET_DIR", "~/.claude/fleet"))

# event -> (waiting on the human?, short label)
WAITING = {
    "SessionStart":     (False, "jacked in"),
    "UserPromptSubmit": (False, "prompt"),
    "PostToolUse":      (False, "tool"),
    "Notification":     (True,  "notification"),
    "Stop":             (True,  "turn done"),
    "SessionEnd":       (None,  "ended"),
}


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        return
    d = json.loads(raw)
    sid = d.get("session_id")
    ev = d.get("hook_event_name")
    if not sid or ev not in WAITING:
        return
    waiting, label = WAITING[ev]
    out = {
        "session_id": sid,
        "cwd": d.get("cwd"),
        "transcript_path": d.get("transcript_path"),
        "event": ev,
        "label": label,
        "waiting": waiting,
        "ended": ev == "SessionEnd",
        "notification": d.get("notification_type") or (d.get("message") if ev == "Notification" else None),
        "tool": d.get("tool_name") if ev == "PostToolUse" else None,
        "tmux_pane": os.environ.get("TMUX_PANE"),
        "pid": os.getppid(),
        "ts": time.time(),
    }
    os.makedirs(FLEET_DIR, exist_ok=True)
    path = os.path.join(FLEET_DIR, f"{sid}.event.json")
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(out, f)
    os.replace(tmp, path)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
