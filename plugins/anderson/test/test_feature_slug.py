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


class TestSeed(TestSlugWithSlash):
    """`feature.sh seed`: state.md first, idempotent, flag-tolerant; what /anderson:start runs as its preamble."""
    def test_seed_writes_state_and_gitignore_without_running_anything(self):
        r = self.run_feature("seed", "amcleanjanet/ar-9-thing", "make", "it", "so")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("seeded", r.stdout)
        t = (self.repo / "feature-research" / "ar-9-thing" / "state.md").read_text()
        self.assertIn("stage:           plan\n", t); self.assertIn("branch:          amcleanjanet/ar-9-thing\n", t)
        self.assertIn("feature-research/", (self.repo / ".gitignore").read_text())
        self.assertFalse((self.repo / "feature-research" / "ar-9-thing" / "run.log").exists())   # no claude call

    def test_seed_is_idempotent_and_keeps_progress(self):
        self.run_feature("seed", "t1")
        state = self.repo / "feature-research" / "t1" / "state.md"
        state.write_text(state.read_text().replace("stage:           plan", "stage:           grill"))
        r = self.run_feature("seed", "t1")
        self.assertIn("already there (stage grill", r.stdout)
        self.assertIn("stage:           grill", state.read_text())

    def test_seed_opus_flag_anywhere_in_the_first_words(self):
        r = self.run_feature("seed", "--opus", "t2")
        self.assertIn("review_model opus", r.stdout)
        self.assertIn("review_model:    opus", (self.repo / "feature-research" / "t2" / "state.md").read_text())
        self.assertEqual(self.run_feature("seed", "--opus").returncode, 64)


if __name__ == "__main__":
    unittest.main()
