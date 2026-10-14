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
- plan_tally: NIOBE 1/1
"""

PLAN = """# demo - plan
**Tier:** NORMAL - plan_review opus/high
## Scorecard
| Dimension | Planner | Reviewer | Why |
|-----------|---------|----------|-----|
| Risk (10 = could break prod; 0 = cosmetic) | 5 | 5 | x |
| Testability (0-3 unit only) | 4 | 5 | x |
| Coupling (10 = entangled) | 7 | 7 | x |
"""


def seat(stage, tokens, start, end):
    return json.dumps({"stage": stage, "seat": "S", "model": "opus/high", "tokens": tokens, "start": start, "end": end})


# two overlapping plan_review seats (span 0..120000) + one implement seat
LEDGER = "\n".join([seat("plan_review", 1000, 0, 60000), seat("plan_review", 2000, 30000, 120000),
                    seat("implement", 4000, 200000, 380000)]) + "\n"


class TestRunlog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.task = os.path.join(self.tmp, "demo")
        os.makedirs(self.task)
        with open(os.path.join(self.task, "state.md"), "w") as f:
            f.write(STATE)
        self.write("plan.md", PLAN)
        self.write("cost.jsonl", LEDGER)
        self.env = dict(os.environ, ANDERSON_RUNLOG=os.path.join(self.tmp, "runs.jsonl"))

    def write(self, name, text):
        with open(os.path.join(self.task, name), "w") as f:
            f.write(text)

    def log_lines(self):
        with open(self.env["ANDERSON_RUNLOG"]) as f:
            return [json.loads(line) for line in f]

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
        self.assertEqual(rec["plan_tally"], {"NIOBE": [1, 1]})
        self.assertEqual(rec["outcome"], "shipped")
        self.assertEqual(rec["cost"], {"plan_review": {"tokens": 3000, "ms": 120000},
                                       "implement": {"tokens": 4000, "ms": 180000}})
        self.assertEqual((rec["tokens"], rec["duration_ms"]), (7000, 300000))
        self.assertEqual(rec["scorecard"], {"risk": 5, "testability": 4, "coupling": 7})
        self.assertEqual(rec["tier_line"], "NORMAL - plan_review opus/high")
        out = self.run_log("--summary")
        self.assertRegex(out, r"hard\s+runs\s+1 · tokens med 7k · time med 5m · rework 1/1")
        self.assertIn("runs 1 · shipped 1", out)
        self.assertIn("rework rounds avg 2.0", out)
        self.assertRegex(out, r"SERAPH\s+seated\s+1 · confirmed 2/3 raised")
        self.assertRegex(out, r"NIOBE\s+seated\s+0 · confirmed 0/0 raised")
        self.assertRegex(out, r"NIOBE\s+plan review · confirmed 1/1 raised")
        self.assertNotIn("SERAPH       plan review", out)

    def test_old_lines_and_garbage_ledger_print_na(self):
        old = {"outcome": "shipped", "state": {"tier": "normal", "iteration": "1"}, "crew_tally": {}}
        with open(self.env["ANDERSON_RUNLOG"], "w") as f:
            f.write(json.dumps(old) + "\n")
        bad = ["not json", json.dumps({"stage": ["x"], "tokens": 1, "start": 0, "end": 1}),
               json.dumps({"stage": "plan", "tokens": "9", "start": 0, "end": 1}),
               '{"stage": "plan", "tokens": 1, "start": NaN, "end": 1}',
               json.dumps({"stage": "plan", "tokens": True, "start": 0, "end": 1})]
        self.write("cost.jsonl", "\n".join(bad) + "\n")
        self.run_log(self.task, "--mode", "gated", "--outcome", "shipped")
        self.assertNotIn("cost", self.log_lines()[-1])
        out = self.run_log("--summary")
        self.assertRegex(out, r"normal\s+runs\s+1 · tokens med n/a · time med n/a · rework 0/1")
        self.assertRegex(out, r"hard\s+runs\s+1 · tokens med n/a · time med n/a · rework 1/1")

    def test_huge_numbers_and_stage_gaps(self):
        row = lambda st, a, b, t=1: json.dumps({"stage": st, "tokens": t, "start": a, "end": b})
        self.write("cost.jsonl", "\n".join([row("diff_review", 0, 60000), row("diff_review", 3600000, 3660000),
                                            row("plan", 0, 10, 10 ** 400)]) + "\n")
        with open(os.path.join(self.task, "plan.md"), "w") as f:
            f.write("| Risk | " + "9" * 5000 + " |\n")
        self.run_log(self.task, "--mode", "gated", "--outcome", "shipped")
        line = self.log_lines()[-1]
        self.assertEqual(line["cost"]["diff_review"]["ms"], 120000)
        self.assertNotIn("plan", line["cost"])  # the 10**400 line is dropped, not logged
        self.assertNotIn("risk", line["scorecard"])
        self.assertRegex(self.run_log("--summary"), r"tokens med \d+k")  # a huge value never reaches median()
        # Three near-limit lines whose sum would cross json's int digit limit are dropped too.
        self.write("cost.jsonl", "\n".join(row("plan", 0, 10, 10 ** 4299) for _ in range(3)) + "\n")
        self.run_log(self.task, "--mode", "gated", "--outcome", "shipped")
        self.assertNotIn("cost", self.log_lines()[-1])

    def test_record_consumes_the_ledger(self):
        self.run_log(self.task, "--mode", "gated", "--outcome", "aborted:x")
        self.assertFalse(os.path.exists(os.path.join(self.task, "cost.jsonl")))
        self.run_log(self.task, "--mode", "gated", "--outcome", "shipped")
        first, second = self.log_lines()
        self.assertIn("cost", first)
        self.assertNotIn("cost", second)

    def test_summary_with_no_log(self):
        self.assertIn("no runs logged yet", self.run_log("--summary"))


if __name__ == "__main__":
    unittest.main()
