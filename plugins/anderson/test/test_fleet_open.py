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
            self.assertIsNotNone(cmd)
            self.assertNotEqual(cmd[0], "vim")
            fleet.EDITOR = "definitely-not-installed-editor"   # unknown/missing: falls through, never crashes
            self.assertIsNotNone(fleet.editor_cmd(self.row, ["/a"]))
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


if __name__ == "__main__":
    unittest.main()
