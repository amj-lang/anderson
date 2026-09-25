"""runlog.py appends one run per call and its summary adds up the crew's hit rate."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

RUNLOG = os.path.join(os.path.dirname(__file__), "..", "bin", "runlog.py")

STATE = """# Pipeline state
<!-- STATE:START -->
task:            demo
stage:           done
iteration:       3
tier:            hard
crew:            SERAPH + MEROVINGIAN
diff_verdict:    ship
<!-- STATE:END -->

## Done so far
- crew_tally: SERAPH 1/2 · MEROVINGIAN 0/1
- crew_tally: SERAPH 1/1
"""


class TestRunlog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.task = os.path.join(self.tmp, "demo")
        os.makedirs(self.task)
        with open(os.path.join(self.task, "state.md"), "w") as f:
            f.write(STATE)
        self.env = dict(os.environ, ANDERSON_RUNLOG=os.path.join(self.tmp, "runs.jsonl"))

    def run_log(self, *args):
        return subprocess.run([sys.executable, RUNLOG, *args], cwd=self.tmp, env=self.env,
                              capture_output=True, text=True, check=True).stdout

    def test_record_then_summary(self):
        self.run_log(self.task, "--mode", "gated", "--outcome", "shipped", "--pr", "https://x/pr/1")
        with open(self.env["ANDERSON_RUNLOG"]) as f:
            rec = json.loads(f.readline())
        self.assertEqual(rec["state"]["tier"], "hard")
        self.assertEqual(rec["state"]["crew"], "SERAPH + MEROVINGIAN")
        self.assertEqual(rec["crew_tally"], {"SERAPH": [2, 3], "MEROVINGIAN": [0, 1]})
        self.assertEqual(rec["outcome"], "shipped")
        out = self.run_log("--summary")
        self.assertIn("runs 1 · shipped 1", out)
        self.assertIn("rework rounds avg 2.0", out)
        self.assertRegex(out, r"SERAPH\s+seated\s+1 · confirmed 2/3 raised")
        self.assertRegex(out, r"NIOBE\s+seated\s+0 · confirmed 0/0 raised")

    def test_summary_with_no_log(self):
        self.assertIn("no runs logged yet", self.run_log("--summary"))


if __name__ == "__main__":
    unittest.main()
