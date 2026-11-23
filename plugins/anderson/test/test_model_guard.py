import json
import subprocess
import sys
import unittest
from pathlib import Path

GUARD = Path(__file__).resolve().parent.parent / "hooks" / "model_guard.py"


def run(tool_input):
    out = subprocess.run([sys.executable, str(GUARD)], input=json.dumps({"tool_input": tool_input}),
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)["hookSpecificOutput"] if out.strip() else None


class ModelGuard(unittest.TestCase):
    def test_denies_model_override_on_anderson_seat(self):
        r = run({"subagent_type": "anderson:prototyper", "model": "fable", "prompt": "x"})
        self.assertEqual(r["permissionDecision"], "deny")
        self.assertIn("frontmatter", r["permissionDecisionReason"])

    def test_allows_anderson_seat_without_model(self):
        self.assertIsNone(run({"subagent_type": "anderson:reviewer-fable", "prompt": "x"}))

    def test_ignores_other_agents(self):
        self.assertIsNone(run({"subagent_type": "Explore", "model": "haiku", "prompt": "x"}))

    def test_wired_in_hooks_json(self):
        hooks = json.loads((GUARD.parent / "hooks.json").read_text())["hooks"]["PreToolUse"]
        self.assertTrue(any(h.get("matcher") == "Agent|Task" and "model_guard.py" in h["hooks"][0]["command"]
                            for h in hooks))


if __name__ == "__main__":
    unittest.main()
