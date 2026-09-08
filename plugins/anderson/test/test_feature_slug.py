"""feature.sh: a slug with a slash keeps the state dir flat and ships on the slug as branch."""
import os, pathlib, shutil, subprocess, tempfile, unittest

FEATURE = pathlib.Path(__file__).resolve().parents[1] / "bin" / "feature.sh"
FAKE_CLAUDE = '#!/usr/bin/env bash\necho \'{"result":"stub"}\'\n'


class TestSlugWithSlash(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        fake = pathlib.Path(self.tmp) / "fakebin"; fake.mkdir()
        (fake / "claude").write_text(FAKE_CLAUDE); (fake / "claude").chmod(0o755)
        (fake / "gh").write_text("#!/usr/bin/env bash\nexit 1\n"); (fake / "gh").chmod(0o755)
        self.repo = pathlib.Path(self.tmp) / "repo"; self.repo.mkdir()
        self.env = {**os.environ, "PATH": f"{fake}:{os.environ['PATH']}", "NO_COLOR": "1",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        for cmd in (["git", "init", "-q", "-b", "main"], ["git", "commit", "-q", "--allow-empty", "-m", "init"]):
            subprocess.run(cmd, cwd=self.repo, env=self.env, check=True, capture_output=True)

    def run_feature(self, *args):
        return subprocess.run(["bash", str(FEATURE), *args], cwd=self.repo, env=self.env, capture_output=True, text=True)

    def test_flat_dir_and_branch_field(self):
        r = self.run_feature("start", "amcleanjanet/ar-2587-ui-polish", "polish the table")
        self.assertEqual(r.returncode, 10, r.stdout + r.stderr)          # halted at the plan gate
        state = self.repo / "feature-research" / "ar-2587-ui-polish" / "state.md"
        self.assertTrue(state.exists(), list((self.repo / "feature-research").rglob("*")))
        self.assertFalse((self.repo / "feature-research" / "amcleanjanet").exists())
        t = state.read_text()
        self.assertIn("task:            ar-2587-ui-polish\n", t)
        self.assertIn("branch:          amcleanjanet/ar-2587-ui-polish\n", t)

    def test_plain_slug_has_no_branch_field(self):
        r = self.run_feature("start", "plain-slug", "goal")
        self.assertEqual(r.returncode, 10, r.stdout + r.stderr)
        t = (self.repo / "feature-research" / "plain-slug" / "state.md").read_text()
        self.assertNotIn("branch:", t)

    def test_ship_uses_slug_as_branch(self):
        self.run_feature("start", "amcleanjanet/ar-2587-ui-polish", "polish")
        (self.repo / "feature-research" / "ar-2587-ui-polish" / "plan.md").write_text("# plan\n## What\nx\n")
        (self.repo / "change.txt").write_text("hello\n")
        r = self.run_feature("--approve-diff", "amcleanjanet/ar-2587-ui-polish")
        self.assertIn("Branch: amcleanjanet/ar-2587-ui-polish", r.stdout, r.stdout + r.stderr)
        head = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=self.repo, env=self.env, capture_output=True, text=True).stdout.strip()
        self.assertEqual(head, "amcleanjanet/ar-2587-ui-polish")


if __name__ == "__main__":
    unittest.main()
