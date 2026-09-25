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


if __name__ == "__main__":
    unittest.main()
