#!/usr/bin/env python3
"""
Optional autonomous scheduler. With this hook enabled, after each agent finishes
the loop advances state.md and emits hook JSON to chain the next agent (or a HALT
notice at a human gate) — so you can run hands-off between gates instead of
issuing each /claude-loop:* command. Leave it out to drive purely via slash commands
or the headless feature.sh.
"""
import glob, json, os, re, sys

NEXT = {
    "plan":        ("plan_review", False, "Use the plan-reviewer subagent. stage=plan_review."),
    "plan_review": ("plan_review", True,  None),
    "implement":   ("diff_review", False, "Use the reviewer subagent. stage=diff_review."),
    "diff_review": ("diff_review", True,  None),
}

def field(t, k):
    m = re.search(
        rf"^\s*(?:[-*]\s+)?\**{re.escape(k)}\**\s*:\s*\**\s*(.*?)\s*\**\s*(?:#.*)?$",
        t, re.M)
    return m.group(1).strip() if m else None

def setf(t, k, v):
    return re.sub(rf"^(\s*(?:[-*]\s+)?\**{re.escape(k)}\**\s*:\s*\**).*?(\**\s*)$",
                  rf"\g<1>{v}\g<2>", t, flags=re.M)

def emit(obj):
    print(json.dumps(obj))

# Read stdin (re-entrancy guard must fire first, before any mutation or emit)
try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

if data.get("stop_hook_active") is True:
    sys.exit(0)

hook_event = data.get("hook_event_name", "SubagentStop")

states = sorted(glob.glob("feature-research/*/state.md"), key=os.path.getmtime)
if not states: sys.exit(0)
path = states[-1]; t = open(path).read()
stage, task = field(t, "stage"), field(t, "task")
if stage in (None, "done") or stage not in NEXT: sys.exit(0)
if stage == "implement" and int(field(t, "iteration") or 0) > int(field(t, "max_iterations") or 2):
    notice = f"EXIT: {task} hit max_iterations. Escalating to you."
    emit({"hookSpecificOutput": {"hookEventName": hook_event, "additionalContext": notice}})
    sys.exit(0)
nxt, gate, directive = NEXT[stage]; t = setf(t, "stage", nxt)
if gate:
    v = field(t, "diff_verdict" if nxt == "diff_review" else "plan_verdict")
    open(path, "w").write(setf(t, "gate", "human"))
    notice = f"HUMAN GATE ({nxt}) for '{task}', verdict={v}. Review feature-research/{task}/, then approve."
    emit({"hookSpecificOutput": {"hookEventName": hook_event, "additionalContext": notice}})
else:
    open(path, "w").write(setf(t, "gate", "none"))
    emit({"decision": "block", "reason": f"{directive} task='{task}'."})
