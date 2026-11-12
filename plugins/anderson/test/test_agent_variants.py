"""The twins (-fable, -medium) exist because the band reads model and effort from agent frontmatter
(the spawn event carries no per-call effort). Their instructions must never drift from the base agent they twin."""
import os
import unittest

AGENTS = os.path.join(os.path.dirname(__file__), "..", "agents")
# (base, twin suffix, twin model, twin effort): -fable escalates the model, -medium lowers the effort
TWINS = [("plan-reviewer", "fable", "fable", "high"), ("reviewer", "fable", "fable", "high"),
         ("plan-reviewer", "medium", "opus", "medium"), ("reviewer", "medium", "opus", "medium")]


def split(name):
    with open(os.path.join(AGENTS, name + ".md"), encoding="utf-8") as f:
        _, fm, body = f.read().split("---\n", 2)
    return dict(line.split(":", 1) for line in fm.strip().splitlines()), body


class TestEffortTwins(unittest.TestCase):
    def test_twins_match_base(self):
        for base, suffix, model, effort in TWINS:
            twin = f"{base}-{suffix}"
            with self.subTest(twin=twin):
                bfm, bbody = split(base)
                tfm, tbody = split(twin)
                self.assertEqual(tbody, bbody, f"{twin}.md body drifted: copy the body of {base}.md")
                self.assertEqual(tfm["name"].strip(), twin)
                self.assertEqual((tfm["model"].strip(), tfm["effort"].strip()), (model, effort))
                self.assertEqual((bfm["model"].strip(), bfm["effort"].strip()), ("opus", "high"))
                for k in ("tools", "color"):
                    self.assertEqual(tfm[k], bfm[k], f"{twin}.md frontmatter '{k}' drifted")

    def test_no_xhigh_seat_is_left(self):
        """0.76.0: the escalation seat is fable/high; nothing runs opus/xhigh."""
        for name in os.listdir(AGENTS):
            with open(os.path.join(AGENTS, name), encoding="utf-8") as f:
                self.assertNotIn("effort: xhigh", f.read(), name)


COMMANDS = os.path.join(os.path.dirname(__file__), "..", "commands")
DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")


class TestTierRuleDrift(unittest.TestCase):
    """The tier rules are stated in four files; they must all state the same ones."""
    FILES = {"tiering": os.path.join(DOCS, "tiering.md"), "start": os.path.join(COMMANDS, "start.md"),
             "auto": os.path.join(COMMANDS, "auto.md"), "approve-plan": os.path.join(COMMANDS, "approve-plan.md")}

    def text(self, name):
        with open(self.FILES[name], encoding="utf-8") as f:
            return f.read()

    def test_new_thresholds_everywhere_old_ones_nowhere(self):
        for name in ("tiering", "start", "auto"):
            for want in ("Coupling ≥ 8", "Confidence ≤ 3"):
                self.assertIn(want, self.text(name), f"{name}.md lacks {want}")
        for name in ("tiering", "approve-plan", "auto"):
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


class TestAutoGrillHandoff(unittest.TestCase):
    """Auto stops on a 🔴 question and start.md must pick the task up at the grill."""

    def test_handoff_both_sides(self):
        with open(os.path.join(COMMANDS, "auto.md"), encoding="utf-8") as f:
            auto = f.read()
        with open(os.path.join(COMMANDS, "start.md"), encoding="utf-8") as f:
            start = f.read()
        self.assertIn("`mode: gated`, `stage: grill`", auto)
        self.assertIn("RESUME FROM AUTO", start)
        self.assertIn("`stage: grill`", start[start.index("RESUME FROM AUTO"):][:300])
        self.assertIn("NO 🔴 AND NO 🎨", start)


class TestLeanTrivial(unittest.TestCase):
    """TRIVIAL is plan → grill → plan review → implement: no crew, no diff reviewer, in both modes."""

    def text(self, name):
        with open(os.path.join(COMMANDS, name), encoding="utf-8") as f:
            return f.read()

    def test_tier_is_routed_before_the_grill(self):
        start = self.text("start.md")
        self.assertLess(start.index("3b. ROUTE"), start.index("4. GRILL"))
        self.assertIn("TRIVIAL GRILL", start)

    def test_trivial_skips_the_diff_reviewer_everywhere(self):
        for name in ("start.md", "approve-plan.md", "auto.md"):
            with self.subTest(name=name):
                t = self.text(name)
                self.assertIn("NO DIFF REVIEW", t)
                if name != "approve-plan.md":  # approve-plan starts after the plan review
                    self.assertIn("plan-reviewer-medium", t)
        with open(os.path.join(DOCS, "tiering.md"), encoding="utf-8") as f:
            self.assertIn("NO DIFF REVIEW", f.read())

    def test_fable_twins_are_named_where_the_tier_escalates(self):
        self.assertIn("plan-reviewer-fable", self.text("start.md"))
        self.assertIn("reviewer-fable", self.text("approve-plan.md"))
        auto = self.text("auto.md")
        self.assertIn("plan-reviewer-fable", auto)
        self.assertIn("reviewer-fable", auto)
        for name in ("start.md", "approve-plan.md", "auto.md", "status.md", "help.md"):
            self.assertNotIn("xhigh", self.text(name), name)


if __name__ == "__main__":
    unittest.main()
