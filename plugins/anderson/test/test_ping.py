"""ping.py: counts a version once per machine, and not at all when opted out."""
import importlib.util, json, pathlib, tempfile, unittest

HOOKS = pathlib.Path(__file__).resolve().parents[1] / "hooks"
_spec = importlib.util.spec_from_file_location("ping", HOOKS / "ping.py")
ping = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ping)


class TestClaim(unittest.TestCase):
    def test_a_version_is_claimed_once_then_never_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            mark = pathlib.Path(tmp) / "sub" / "counted"      # creates the directory too
            self.assertTrue(ping.claim("1.0.0", mark))
            self.assertFalse(ping.claim("1.0.0", mark))
            self.assertTrue(ping.claim("1.1.0", mark))        # an update counts again
            self.assertFalse(ping.claim("1.1.0", mark))
            self.assertEqual(mark.read_text().split(), ["1.0.0", "1.1.0"])


class TestOptOut(unittest.TestCase):
    def test_either_variable_opts_out(self):
        self.assertTrue(ping.opted_out({"ANDERSON_NO_TELEMETRY": "1"}))
        self.assertTrue(ping.opted_out({"DO_NOT_TRACK": "1"}))
        self.assertFalse(ping.opted_out({}))


class TestVersion(unittest.TestCase):
    def test_version_comes_from_the_plugin_manifest(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        manifest = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(ping.version(), manifest["version"])


if __name__ == "__main__":
    unittest.main()
