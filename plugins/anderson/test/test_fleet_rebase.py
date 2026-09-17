"""fleet.py `R`: rebase this checkout onto main/master and force-push that one branch.
Real git repos with a real bare origin — the point of the feature is what git actually does to the
remote, so only the GitHub protection lookup is stubbed."""
import importlib.util, os, pathlib, subprocess, tempfile, unittest

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin"
_spec = importlib.util.spec_from_file_location("fleet_rebase", BIN / "fleet.py")
fleet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet)

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def git(cwd, *a):
    return subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, env=ENV, check=True).stdout.strip()


def identify(cwd):
    """A committer for the repo itself: fleet shells out to git with the ambient environment, and a
    CI runner has no global user.name (a rebase needs one to write commits)."""
    git(cwd, "config", "user.name", "t"); git(cwd, "config", "user.email", "t@t")


def commit(cwd, name, text):
    pathlib.Path(cwd, name).write_text(text)
    git(cwd, "add", name); git(cwd, "commit", "-qm", f"add {name}")


class TestRebaseRow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.origin = os.path.join(self.tmp, "origin.git")
        seed = os.path.join(self.tmp, "seed")
        subprocess.run(["git", "init", "-q", "-b", "main", seed], capture_output=True, check=True)
        identify(seed); commit(seed, "base", "1")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.origin], capture_output=True, check=True)
        git(seed, "remote", "add", "origin", self.origin); git(seed, "push", "-q", "origin", "main")
        self.repo = os.path.join(self.tmp, "work")
        subprocess.run(["git", "clone", "-q", self.origin, self.repo], capture_output=True, env=ENV, check=True)
        identify(self.repo)
        git(self.repo, "checkout", "-qb", "feat")
        commit(self.repo, "mine", "mine")
        git(self.repo, "push", "-q", "-u", "origin", "feat")
        # main moves on the remote, behind the branch's back
        git(seed, "checkout", "-q", "main"); commit(seed, "theirs", "theirs"); git(seed, "push", "-q", "origin", "main")
        self.protected = True
        fleet.base_protected = lambda path, base: self.protected

    def remote_sha(self, ref):
        return git(self.origin, "rev-parse", ref)

    def test_rebases_onto_origin_main_and_force_pushes_only_that_branch(self):
        main_before = self.remote_sha("main")
        msg = fleet.rebase_row(self.repo)
        self.assertIn("force-pushed", msg)
        # the branch now sits on top of the remote main, locally and on the remote
        self.assertEqual(git(self.repo, "rev-parse", "HEAD~1"), main_before)
        self.assertEqual(self.remote_sha("feat"), git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(self.remote_sha("main"), main_before)          # the base is never pushed

    def test_conflicts_abort_and_push_nothing(self):
        feat_before = self.remote_sha("feat")
        seed = os.path.join(self.tmp, "seed")
        git(seed, "rm", "-q", "theirs"); pathlib.Path(seed, "clash").write_text("theirs")
        git(seed, "add", "clash"); git(seed, "commit", "-qm", "clash"); git(seed, "push", "-q", "origin", "main")
        pathlib.Path(self.repo, "clash").write_text("mine")
        git(self.repo, "add", "clash"); git(self.repo, "commit", "-qm", "clash mine")
        head = git(self.repo, "rev-parse", "HEAD")
        msg = fleet.rebase_row(self.repo)
        self.assertIn("CONFLICTS", msg)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), head)     # rebase aborted, work intact
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        self.assertEqual(self.remote_sha("feat"), feat_before)          # nothing pushed
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".git", "rebase-merge")))

    def test_unprotected_base_refuses_before_touching_anything(self):
        for prot, why in ((False, "NOT protected"), (None, "cannot verify")):
            self.protected = prot
            head = git(self.repo, "rev-parse", "HEAD")
            msg = fleet.rebase_row(self.repo)
            self.assertIn("REFUSED", msg)
            self.assertIn(why, msg)
            self.assertEqual(git(self.repo, "rev-parse", "HEAD"), head)
            self.assertEqual(self.remote_sha("feat"), head)

    def test_on_the_base_branch_itself_it_refuses(self):
        git(self.repo, "checkout", "-q", "main")
        self.assertIn("never the base", fleet.rebase_row(self.repo))

    def test_dirty_tree_refuses(self):
        pathlib.Path(self.repo, "mine").write_text("edited")
        self.assertIn("uncommitted changes", fleet.rebase_row(self.repo))

    def test_a_worktree_rebases_like_any_other_checkout(self):
        wt = os.path.join(self.tmp, "wt")
        git(self.repo, "checkout", "-q", "main")
        subprocess.run(["git", "-C", self.repo, "worktree", "add", "-q", wt, "feat"],
                       capture_output=True, env=ENV, check=True)
        self.assertIn("force-pushed", fleet.rebase_row(wt))
        self.assertEqual(self.remote_sha("feat"), git(wt, "rev-parse", "HEAD"))

    def test_plain_directory_is_not_a_checkout(self):
        self.assertIn("not a git checkout", fleet.rebase_row(self.tmp))


class TestProtectionLookup(unittest.TestCase):
    def test_no_gh_on_path_reads_as_unknown(self):
        old = fleet.shutil.which
        fleet.shutil.which = lambda n: None
        try:
            self.assertIsNone(fleet.base_protected("/tmp", "main"))
        finally:
            fleet.shutil.which = old

    def test_api_answer_maps_to_true_false_unknown(self):
        old_which, old_sh = fleet.shutil.which, fleet._sh
        answers = {}
        fleet.shutil.which = lambda n: "/usr/bin/gh"
        fleet._sh = lambda cmd, cwd, timeout=20: answers.get("repo" if "repo" in cmd else "api")
        try:
            answers = {"repo": "o/r", "api": "true"}
            self.assertIs(fleet.base_protected("/x", "main"), True)
            answers = {"repo": "o/r", "api": "false"}
            self.assertIs(fleet.base_protected("/x", "main"), False)
            answers = {"repo": "o/r", "api": None}          # API refused
            self.assertIsNone(fleet.base_protected("/x", "main"))
            answers = {"repo": None}                        # not a GitHub remote
            self.assertIsNone(fleet.base_protected("/x", "main"))
        finally:
            fleet.shutil.which, fleet._sh = old_which, old_sh


if __name__ == "__main__":
    unittest.main()
