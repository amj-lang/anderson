#!/usr/bin/env python3
"""
Optional autonomous scheduler. With this hook enabled, after each agent finishes
the loop advances state.md and emits hook JSON to chain the next agent (or a HALT
notice at a human gate) — so you can run hands-off between gates instead of
issuing each /anderson:* command. Leave it out to drive purely via slash commands
or the headless feature.sh.
"""
import glob, json, os, re, sys

NEXT = {
    "plan":        ("grill",       "grill", None),
    "plan_review": ("plan_review", True,    None),
    "implement":   ("diff_review", False,   "Use the reviewer subagent. stage=diff_review."),
    "diff_review": ("diff_review", True,    None),
}
# 'grill' is deliberately NOT a key: once stage=grill the hook exits silently and
# never auto-advances past it, so the human interview can't be skipped. The
# grill -> plan_review transition is driven by /anderson:start once you're satisfied.

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

def main():
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
    # plan-review asked for another grill pass: route back, human-gated. The grill
    # step (no NEXT key) is the loop guard, so no counter/state field is needed.
    # Reset plan_verdict so the next plan_review starts clean and doesn't re-bounce.
    if stage == "plan_review" and field(t, "plan_verdict") == "regrill":
        t = setf(setf(t, "stage", "grill"), "plan_verdict", "pending")
        open(path, "w").write(setf(t, "gate", "human"))
        notice = (f"RE-GRILL ('{task}'): plan-review returned `regrill`. Back to the grill "
                  "step — interview the open decisions one at a time, fold answers into "
                  "plan.md, then advance to plan-review again. No subagent runs here.")
        emit({"hookSpecificOutput": {"hookEventName": hook_event, "additionalContext": notice}})
        sys.exit(0)
    nxt, gate, directive = NEXT[stage]; t = setf(t, "stage", nxt)
    if gate == "grill":
        open(path, "w").write(setf(t, "gate", "human"))
        notice = (f"GRILL ('{task}'): plan drafted. Grill it now — relentless, one question at "
                  "a time, down each branch of the decision tree, recommending an answer to each; "
                  "explore the codebase instead of asking when you can; fold every resolved "
                  "decision into plan.md. When you're satisfied it advances to plan-review. "
                  "No subagent runs here — this step is you.")
        emit({"hookSpecificOutput": {"hookEventName": hook_event, "additionalContext": notice}})
    elif gate:
        v = field(t, "diff_verdict" if nxt == "diff_review" else "plan_verdict")
        open(path, "w").write(setf(t, "gate", "human"))
        notice = f"HUMAN GATE ({nxt}) for '{task}', verdict={v}. Review feature-research/{task}/, then approve."
        emit({"hookSpecificOutput": {"hookEventName": hook_event, "additionalContext": notice}})
    else:
        open(path, "w").write(setf(t, "gate", "none"))
        emit({"decision": "block", "reason": f"{directive} task='{task}'."})

if __name__ == "__main__":
    main()
