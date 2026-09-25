"""The -xhigh agents exist only because effort is frontmatter-only (the Agent tool has no per-call
effort). Their instructions must never drift from the base agent they twin."""
import os
import unittest

AGENTS = os.path.join(os.path.dirname(__file__), "..", "agents")


def split(name):
    with open(os.path.join(AGENTS, name + ".md"), encoding="utf-8") as f:
        _, fm, body = f.read().split("---\n", 2)
    return dict(line.split(":", 1) for line in fm.strip().splitlines()), body


class TestXhighTwins(unittest.TestCase):
    def test_twins_match_base(self):
        for base in ("plan-reviewer", "reviewer"):
            with self.subTest(base=base):
                bfm, bbody = split(base)
                tfm, tbody = split(base + "-xhigh")
                self.assertEqual(tbody, bbody, f"{base}-xhigh.md body drifted: copy the body of {base}.md")
                self.assertEqual(tfm["name"].strip(), base + "-xhigh")
                self.assertEqual(tfm["effort"].strip(), "xhigh")
                self.assertEqual(bfm["effort"].strip(), "high")
                for k in ("tools", "model", "color"):
                    self.assertEqual(tfm[k], bfm[k], f"{base}-xhigh.md frontmatter '{k}' drifted")


if __name__ == "__main__":
    unittest.main()
