#!/usr/bin/env python3
"""
fleet event hook — records the last lifecycle event of a Claude Code session in
~/.claude/fleet/<session_id>.event.json so bin/fleet.py (THE OPERATOR) can tell
"waiting on you" (Stop / Notification) from "working" (UserPromptSubmit / PostToolUse)
without guessing from the transcript. Wired for SessionStart, UserPromptSubmit,
PostToolUse, Notification, Stop, SessionEnd in hooks/hooks.json.

Emits nothing on stdout: this hook never steers the session. Never raises.
"""
import json, os, re, sys, time

FLEET_DIR = os.path.expanduser(os.environ.get("ANDERSON_FLEET_DIR", "~/.claude/fleet"))

TASK_PATH = re.compile(r"feature-research/([^/\s]+)/")
TASK_CMD = re.compile(r"/anderson:(?:start|auto|rework|approve-plan|approve-diff|status)\s+([^\s]+)")


def session_task(d, prev):
    """Which anderson task THIS session is on. Two sessions can share one checkout, so the newest
    state.md under the repo is not an answer -- the session that writes `feature-research/<task>/`
    is the one that owns it. Read off the tool this session just ran, else the slash command it was
    given; sticky, because most events (a Bash call, a Stop) say nothing about the task."""
    ti = d.get("tool_input") or {}
    hay = " ".join(str(ti.get(k) or "") for k in ("file_path", "path", "command", "pattern"))
    m = TASK_PATH.search(hay) or TASK_CMD.search(str(d.get("prompt") or ""))
    return m.group(1) if m else prev


def claude_pid(start):
    """Walk up from `start` to the `claude` process. Statusline/hook commands run under one or two
    shells, and a backgrounded emitter gets reparented to launchd (pid 1), so getppid() alone lies."""
    import subprocess
    pid = start
    for _ in range(8):
        if not pid or int(pid) <= 1:
            return None
        try:
            r = subprocess.run(["ps", "-o", "ppid=,command=", "-p", str(pid)], capture_output=True, text=True, timeout=2)
            parts = r.stdout.strip().split(None, 1)
        except Exception:
            return None
        if len(parts) < 2:
            return None
        head = parts[1].split()[:2]
        if any(os.path.basename(h) == "claude" or "claude-code" in h for h in head):
            return int(pid)
        pid = parts[0]
    return None

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
    path = os.path.join(FLEET_DIR, f"{sid}.event.json")
    try:
        prev = json.load(open(path)).get("task")
    except Exception:
        prev = None
    out = {
        "task": session_task(d, prev),
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
        "pid": claude_pid(int(os.environ.get("FLEET_PID") or os.getppid())),
        "ts": time.time(),
    }
    os.makedirs(FLEET_DIR, exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(out, f)
    os.replace(tmp, path)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
