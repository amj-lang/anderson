"""Statusline shows the *active* review model (fable default / opus override), not a hardcoded one."""
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
    def test_opus_review_model(self):
        out = _run("task: x\nstage: plan_review\nreview_model: opus\n")
        self.assertIn(b"opus/xhigh", out.stdout)

    def test_missing_review_model_defaults_fable(self):
        out = _run("task: x\nstage: diff_review\n")
        self.assertIn(b"fable/high", out.stdout)


if __name__ == "__main__":
    unittest.main()
