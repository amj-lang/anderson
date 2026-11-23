#!/usr/bin/env python3
"""PreToolUse(Agent): an anderson seat runs the model its frontmatter declares.

The Agent tool's `model` param outranks agent frontmatter, so an orchestrator that "upgrades"
a seat (prototyper or planner on fable) silently breaks the tier table. Deny it; the
orchestrator retries without the param. Other plugins' agents pass through untouched.
"""
import json
import sys


def verdict(tool_input):
    """Deny reason for this Agent call, or None to let it through."""
    kind = str(tool_input.get("subagent_type") or "")
    model = tool_input.get("model")
    if not kind.startswith("anderson:") or not model:
        return None
    return (
        f"{kind} runs the model in its agent frontmatter; do not pass model={model!r}. "
        "Re-invoke the same call without the `model` field. A stronger review seat is a "
        "different agent (the -fable twin), picked by tier, never a model override."
    )


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    reason = verdict(event.get("tool_input") or {})
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}))


if __name__ == "__main__":
    main()
