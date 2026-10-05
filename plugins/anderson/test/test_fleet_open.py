"""fleet.py: reading the gate artifact (plan.md / audit.md, then the diff) right in fleet on `o`."""
import importlib.util, os, pathlib, tempfile, unittest

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin"
_spec = importlib.util.spec_from_file_location("fleet_open", BIN / "fleet.py")
fleet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet)


class TestGateOpen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        d = os.path.join(self.tmp, "feature-research", "ar-1")
        os.makedirs(d)
        for f in ("plan.md", "audit.md"):
            open(os.path.join(d, f), "w").write("x")
        self.row = {"root": self.tmp, "cwd": self.tmp, "task": "ar-1", "stage": "diff_review", "gate": "human", "pid": None}

    def names(self, r):
        return [os.path.basename(p) for p in fleet.gate_files(r)]

    def test_gate_files_by_stage(self):
        self.assertEqual(self.names(self.row), ["plan.md", "audit.md"])
        self.assertEqual(self.names({**self.row, "stage": "grill"}), ["plan.md"])
        self.assertEqual(self.names({**self.row, "stage": "plan_review"}), ["plan.md"])
        self.assertEqual(self.names({**self.row, "stage": "implement"}), ["audit.md"])
        self.assertEqual(self.names({**self.row, "task": ""}), [])
        self.assertEqual(self.names({**self.row, "task": "missing"}), [])


class TestReadHere(unittest.TestCase):
    def test_md_ansi_marks_headings_bullets_strike_and_code(self):
        out = fleet.md_ansi("# Plan\n- a **bold** ~~gone~~ `x`\n```\ncode\n```\nplain")
        lines = out.split("\n")
        self.assertTrue(lines[0].startswith("\033[1m\033[32mPlan"))
        self.assertIn("\033[1mbold\033[0m", lines[1]); self.assertIn("\033[9mgone", lines[1])
        self.assertTrue(lines[3].startswith("\033[2mcode"))
        self.assertEqual(lines[5], "plain")

    def test_view_cmd_falls_back_to_less_with_rendered_temp_files(self):
        old = fleet.FLEET_DIR, fleet.shutil.which
        with tempfile.TemporaryDirectory() as tmp:
            fleet.FLEET_DIR = tmp
            fleet.shutil.which = lambda x: None            # no glow anywhere
            try:
                src = os.path.join(tmp, "plan.md"); open(src, "w").write("# T\n- x")
                cmd, tmpfiles = fleet.view_cmd([src])
                self.assertEqual(cmd[:2], ["less", "-R"]); self.assertIn("plan.md", cmd[4])
                self.assertEqual(len(tmpfiles), 1); self.assertIn("\033[", open(tmpfiles[0]).read())
                fleet.shutil.which = lambda x: "/usr/local/bin/glow" if x == "glow" else None
                cmd, tmpfiles = fleet.view_cmd([src])
                self.assertEqual(cmd[:3], ["glow", "-p", "-w"]); self.assertGreaterEqual(int(cmd[3]), 40)
                self.assertEqual(cmd[4], src); self.assertEqual(tmpfiles, [])
            finally:
                fleet.FLEET_DIR, fleet.shutil.which = old

    def test_gate_diff_shows_tracked_and_untracked_but_not_scratch(self):
        import subprocess
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as fd:
            old = fleet.FLEET_DIR; fleet.FLEET_DIR = fd
            try:
                git = lambda *a: subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True)
                git("init", "-q"); open(os.path.join(repo, "a.py"), "w").write("old\n")
                git("add", "."); git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
                row = {"root": repo, "task": "t", "stage": "diff_review"}
                self.assertIsNone(fleet.gate_diff(row))                       # clean tree: no diff page
                open(os.path.join(repo, "a.py"), "w").write("new\n")
                open(os.path.join(repo, "b.py"), "w").write("added\n")
                os.makedirs(os.path.join(repo, "feature-research", "t"))
                open(os.path.join(repo, "feature-research", "t", "plan.md"), "w").write("scratch\n")
                text = open(fleet.gate_diff(row)).read()
                self.assertIn("new", text); self.assertIn("added", text); self.assertNotIn("scratch", text)
                self.assertIsNone(fleet.gate_diff({**row, "stage": "plan_review"}))
                self.assertIsNone(fleet.gate_diff({**row, "root": os.path.join(fd, "nope")}))
            finally:
                fleet.FLEET_DIR = old

    def test_view_gate_without_files_says_so(self):
        self.assertIn("nothing to read", fleet.view_gate({"root": "/nonexistent", "task": "x", "stage": "grill", "pid": None}))


if __name__ == "__main__":
    unittest.main()
