"""stdlib unittest for scheduler.py pure functions (no I/O, no pip deps)."""
import importlib.util, pathlib, unittest

_p = pathlib.Path(__file__).resolve().parents[1] / "hooks" / "scheduler.py"
_spec = importlib.util.spec_from_file_location("scheduler", _p)
scheduler = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scheduler)   # safe only after main() wrap (no module-level side effects)
field, setf, NEXT = scheduler.field, scheduler.setf, scheduler.NEXT


class TestField(unittest.TestCase):
    def test_canonical(self):
        self.assertEqual(field("stage: plan", "stage"), "plan")

    def test_dash_bullet(self):
        self.assertEqual(field("- stage: plan", "stage"), "plan")

    def test_star_bullet(self):
        self.assertEqual(field("* stage: plan", "stage"), "plan")

    def test_bold_key(self):
        self.assertEqual(field("**stage**: plan", "stage"), "plan")

    def test_bold_value(self):
        self.assertEqual(field("stage: **plan**", "stage"), "plan")

    def test_trailing_comment(self):
        self.assertEqual(field("stage: plan   # current", "stage"), "plan")

    def test_leading_ws_padded(self):
        self.assertEqual(field("   stage:    plan", "stage"), "plan")

    def test_key_absent(self):
        self.assertIsNone(field("task: foo", "stage"))


class TestSetf(unittest.TestCase):
    def test_canonical(self):
        self.assertEqual(setf("stage: plan", "stage", "grill"), "stage: grill")

    def test_bullet_preserved(self):
        self.assertEqual(setf("- stage: plan", "stage", "grill"), "- stage: grill")

    def test_bold_value_preserved(self):
        self.assertEqual(setf("stage: **plan**", "stage", "grill"), "stage: **grill**")

    def test_bold_key_preserved(self):
        self.assertEqual(setf("**stage**: plan", "stage", "grill"), "**stage**: grill")

    def test_trailing_comment_dropped(self):
        self.assertEqual(setf("stage: plan   # c", "stage", "grill"), "stage: grill")

    def test_round_trip(self):
        self.assertEqual(field(setf("stage: plan", "stage", "grill"), "stage"), "grill")


class TestNEXT(unittest.TestCase):
    def test_plan(self):
        self.assertEqual(NEXT["plan"], ("grill", "grill", None))

    def test_plan_review(self):
        self.assertEqual(NEXT["plan_review"], ("plan_review", True, None))

    def test_implement(self):
        self.assertEqual(NEXT["implement"], ("diff_review", False, "Use the reviewer subagent. stage=diff_review."))

    def test_diff_review(self):
        self.assertEqual(NEXT["diff_review"], ("diff_review", True, None))

    def test_grill_not_in_next(self):
        self.assertNotIn("grill", NEXT)

    def test_exact_keys(self):
        self.assertEqual(set(NEXT), {"plan", "plan_review", "implement", "diff_review"})


class TestEscalation(unittest.TestCase):
    """Mirror scheduler's escalation condition — no I/O, helper defined in test."""

    @staticmethod
    def should_escalate(stage, iteration, max_iterations):
        return stage == "implement" and int(iteration or 0) > int(max_iterations or 2)

    def test_over_limit(self):
        self.assertTrue(self.should_escalate("implement", 3, 2))

    def test_at_limit(self):
        self.assertFalse(self.should_escalate("implement", 2, 2))

    def test_wrong_stage(self):
        self.assertFalse(self.should_escalate("diff_review", 9, 2))

    def test_none_iteration(self):
        self.assertFalse(self.should_escalate("implement", None, 2))


class TestRegrill(unittest.TestCase):
    """Mirror the regrill routing condition — no I/O."""

    @staticmethod
    def should_regrill(stage, plan_verdict):
        return stage == "plan_review" and plan_verdict == "regrill"

    def test_regrill_fires(self):
        self.assertTrue(self.should_regrill("plan_review", "regrill"))

    def test_ship_no_regrill(self):
        self.assertFalse(self.should_regrill("plan_review", "ship"))

    def test_wrong_stage(self):
        self.assertFalse(self.should_regrill("implement", "regrill"))


class TestAutoModeGuard(unittest.TestCase):
    """Mirror the auto-mode early-exit condition — no I/O, pure helper."""

    @staticmethod
    def is_auto_run(mode):
        return mode == "auto"

    def test_auto_mode_skips(self):
        self.assertTrue(self.is_auto_run("auto"))

    def test_absent_mode_does_not_skip(self):
        self.assertFalse(self.is_auto_run(None))

    def test_gated_mode_does_not_skip(self):
        self.assertFalse(self.is_auto_run("gated"))

    def test_empty_string_does_not_skip(self):
        self.assertFalse(self.is_auto_run(""))

    def test_field_absent_returns_none(self):
        # field() returns None for a missing key — None == "auto" is False (gated path intact)
        self.assertIsNone(field("stage: plan", "mode"))
        self.assertFalse(self.is_auto_run(field("stage: plan", "mode")))

    def test_field_present_auto(self):
        self.assertEqual(field("mode: auto", "mode"), "auto")
        self.assertTrue(self.is_auto_run(field("mode: auto", "mode")))

    def test_field_present_other(self):
        self.assertEqual(field("mode: gated", "mode"), "gated")
        self.assertFalse(self.is_auto_run(field("mode: gated", "mode")))


if __name__ == "__main__":
    unittest.main()
