"""fleet.py: opening the gate artifact (plan.md / audit.md) in an editor on `o` or at a human gate."""
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

    def test_editor_resolution_order(self):
        old = {k: os.environ.get(k) for k in ("VISUAL", "EDITOR", "FLEET_EDITOR")}
        old_editor = fleet.EDITOR
        try:
            for k in old:
                os.environ.pop(k, None)
            fleet.EDITOR = None
            os.environ["EDITOR"] = "vim"                       # terminal editor: not used for GUI opening
            cmd = fleet.editor_cmd(self.row, ["/a"])
            self.assertTrue(cmd is None or cmd[0] != "vim")
            fleet.EDITOR = "definitely-not-installed-editor"   # unknown/missing: falls through, never crashes
            fleet.editor_cmd(self.row, ["/a"])
        finally:
            fleet.EDITOR = old_editor
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_open_gate_without_files_says_so(self):
        self.assertIn("nothing to open", fleet.open_gate({**self.row, "task": "missing"}))

    def test_auto_open_only_at_human_gate(self):
        self.assertEqual(fleet.gate_auto_open({**self.row, "gate": "none"}), "")
        self.assertEqual(fleet.gate_auto_open({**self.row, "task": "missing"}), "")

    def test_auto_open_silent_when_no_editor_applies(self):
        """⏎ on a plain-terminal session must not report an IDE failure over a good jack in."""
        old = fleet.editor_cmd
        try:
            fleet.editor_cmd = lambda r, files: None
            self.assertEqual(fleet.gate_auto_open(self.row), "")
            fleet.editor_cmd = lambda r, files: ["true"] + files
            self.assertIn("plan.md", fleet.gate_auto_open(self.row))
        finally:
            fleet.editor_cmd = old

    def test_editor_pref_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = fleet.FLEET_DIR, fleet.PREFS_FILE
            fleet.FLEET_DIR = tmp; fleet.PREFS_FILE = os.path.join(tmp, "prefs.json")
            try:
                self.assertIsNone(fleet.load_prefs()["editor"])
                fleet.save_prefs(editor="code -g")
                self.assertEqual(fleet.load_prefs()["editor"], "code -g")
            finally:
                fleet.FLEET_DIR, fleet.PREFS_FILE = old


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

    def test_view_gate_without_files_says_so(self):
        self.assertIn("nothing to read", fleet.view_gate({"root": "/nonexistent", "task": "x", "stage": "grill", "pid": None}))

    def test_terminal_owned_session_has_no_ide_to_open(self):
        import sys
        if sys.platform != "darwin":
            self.skipTest("macOS only")
        old = fleet._owner_app, fleet.EDITOR
        try:
            fleet.EDITOR = None
            for k in ("FLEET_EDITOR", "VISUAL", "EDITOR"):
                os.environ.pop(k, None)
            fleet._owner_app = lambda pid: ("Terminal", "/System/Applications/Utilities/Terminal.app")
            self.assertIsNone(fleet.editor_cmd({"pid": 1}, ["/a"]))
            fleet._owner_app = lambda pid: ("WebStorm", "/Applications/WebStorm.app")
            self.assertEqual(fleet.editor_cmd({"pid": 1}, ["/a"]), ["open", "-a", "/Applications/WebStorm.app", "/a"])
        finally:
            fleet._owner_app, fleet.EDITOR = old


if __name__ == "__main__":
    unittest.main()
