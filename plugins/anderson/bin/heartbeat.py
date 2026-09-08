#!/usr/bin/env python3
"""
fleet heartbeat — feed it the statusline JSON Claude Code writes to the statusline's
stdin; it records one small JSON per session in ~/.claude/fleet/<session_id>.status.json
for bin/fleet.py (THE OPERATOR). Called by bin/statusline.sh and bin/fleet-statusline.sh.

Fields: session_id, cwd, transcript_path, model, cost_usd, duration_ms, lines_added,
lines_removed, ctx_pct, ctx_tokens, tmux_pane, pid (the Claude process = our parent), ts.
Never raises: a broken heartbeat must never break the statusline.
"""
import json, os, sys, time

FLEET_DIR = os.path.expanduser(os.environ.get("ANDERSON_FLEET_DIR", "~/.claude/fleet"))


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        return
    d = json.loads(raw)
    sid = d.get("session_id")
    if not sid:
        return
    cost = d.get("cost") or {}
    ctx = d.get("context_window") or {}
    cur = ctx.get("current_usage") or {}
    ctx_tokens = sum(int(cur.get(k) or 0) for k in
                     ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    ctx_pct = ctx.get("used_percentage")
    if ctx_pct is None and ctx.get("context_window_size"):
        ctx_pct = 100.0 * ctx_tokens / float(ctx["context_window_size"])
    model = d.get("model") or {}
    out = {
        "session_id": sid,
        "cwd": d.get("cwd") or (d.get("workspace") or {}).get("current_dir"),
        "transcript_path": d.get("transcript_path"),
        "model": model.get("display_name") or model.get("id"),
        "cost_usd": cost.get("total_cost_usd"),
        "duration_ms": cost.get("total_duration_ms"),
        "lines_added": cost.get("total_lines_added"),
        "lines_removed": cost.get("total_lines_removed"),
        "ctx_pct": ctx_pct,
        "ctx_tokens": ctx_tokens or None,
        "tmux_pane": os.environ.get("TMUX_PANE"),
        "pid": os.getppid(),
        "ts": time.time(),
    }
    os.makedirs(FLEET_DIR, exist_ok=True)
    path = os.path.join(FLEET_DIR, f"{sid}.status.json")
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(out, f)
    os.replace(tmp, path)   # atomic: fleet.py never reads a half-written file


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
