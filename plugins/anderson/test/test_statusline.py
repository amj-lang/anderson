"""Statusline shows the tier-sized review effort, not a hardcoded one."""
import os, pathlib, subprocess, tempfile, unittest

STATUSLINE = pathlib.Path(__file__).resolve().parents[1] / "bin" / "statusline.sh"


def _run(state_body):
    with tempfile.TemporaryDirectory() as tmp:
        fr_dir = pathlib.Path(tmp) / "feature-research" / "x"
        fr_dir.mkdir(parents=True)
        (fr_dir / "state.md").write_text(state_body)
        env = {**os.environ, "NO_COLOR": "1"}
        return subprocess.run(
            ["bash", str(STATUSLINE)], cwd=tmp, env=env, input=b"",
            capture_output=True,
        )


class TestStatusline(unittest.TestCase):
    def test_plan_review_high_until_critical(self):
        self.assertIn(b"opus/high", _run("task: x\nstage: plan_review\ntier: hard\n").stdout)
        self.assertIn(b"opus/xhigh", _run("task: x\nstage: plan_review\ntier: critical\n").stdout)

    def test_diff_review_xhigh_from_hard(self):
        self.assertIn(b"opus/high", _run("task: x\nstage: diff_review\n").stdout)
        self.assertIn(b"opus/xhigh", _run("task: x\nstage: diff_review\ntier: hard\n").stdout)


if __name__ == "__main__":
    unittest.main()
