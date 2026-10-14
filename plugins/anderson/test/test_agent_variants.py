"""The effort twins (-xhigh, -medium) exist only because effort is frontmatter-only (the Agent tool
has no per-call effort). Their instructions must never drift from the base agent they twin."""
import os
import unittest

AGENTS = os.path.join(os.path.dirname(__file__), "..", "agents")
TWINS = [("plan-reviewer", "xhigh"), ("reviewer", "xhigh"), ("reviewer", "medium")]


def split(name):
    with open(os.path.join(AGENTS, name + ".md"), encoding="utf-8") as f:
        _, fm, body = f.read().split("---\n", 2)
    return dict(line.split(":", 1) for line in fm.strip().splitlines()), body


class TestEffortTwins(unittest.TestCase):
    def test_twins_match_base(self):
        for base, effort in TWINS:
            twin = f"{base}-{effort}"
            with self.subTest(twin=twin):
                bfm, bbody = split(base)
                tfm, tbody = split(twin)
                self.assertEqual(tbody, bbody, f"{twin}.md body drifted: copy the body of {base}.md")
                self.assertEqual(tfm["name"].strip(), twin)
                self.assertEqual(tfm["effort"].strip(), effort)
                self.assertEqual(bfm["effort"].strip(), "high")
                for k in ("tools", "model", "color"):
                    self.assertEqual(tfm[k], bfm[k], f"{twin}.md frontmatter '{k}' drifted")


COMMANDS = os.path.join(os.path.dirname(__file__), "..", "commands")
DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")


class TestTierRuleDrift(unittest.TestCase):
    """The tier rules are stated in five files; they must all state the same ones."""
    FILES = {"tiering": os.path.join(DOCS, "tiering.md"), "start": os.path.join(COMMANDS, "start.md"),
             "auto": os.path.join(COMMANDS, "auto.md"), "approve-plan": os.path.join(COMMANDS, "approve-plan.md"),
             "rework": os.path.join(COMMANDS, "rework.md")}

    def text(self, name):
        with open(self.FILES[name], encoding="utf-8") as f:
            return f.read()

    def test_new_thresholds_everywhere_old_ones_nowhere(self):
        for name in ("tiering", "start", "auto"):
            for want in ("Coupling ≥ 8", "Confidence ≤ 3"):
                self.assertIn(want, self.text(name), f"{name}.md lacks {want}")
        for name in ("tiering", "approve-plan", "rework", "auto"):
            for want in ("≥400", "≥15 files"):
                self.assertIn(want, self.text(name), f"{name}.md lacks {want}")
        for name in self.FILES:
            t = self.text(name)
            for old in ("≥150", "≥8 files", "Coupling ≥ 7 OR", "Confidence ≤ 4", "Risk ≥ 9 OR Testability"):
                self.assertNotIn(old, t, f"{name}.md still states {old}")
            self.assertRegex(t, r"only (ever )?escalat|can only escalate", f"{name}.md dropped 'only escalates'")
            self.assertIn("externally reachable entry point", t, f"{name}.md lacks the entry-point clause")

    def test_auto_flags_needs_human_for_testability(self):
        t = self.text("auto")
        labels = t[t.index("Determine labels"):][:700]
        self.assertIn("Testability ≥ 7", labels)


if __name__ == "__main__":
    unittest.main()
