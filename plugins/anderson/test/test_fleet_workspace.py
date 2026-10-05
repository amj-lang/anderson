"""fleet.py workspace mode: the sessions + repos sections, per-workspace hide/fold, the row
viewport, the ⏎ -> prompt -> p/a/A spawn flow, and finding a session's Ghostty tab. Loads bin/fleet.py by path, same
idiom as the other fleet test modules."""
import importlib.util, os, pathlib, subprocess, tempfile, time, unittest
from unittest import mock

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin"
_spec = importlib.util.spec_from_file_location("fleet_workspace", BIN / "fleet.py")
fleet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet)


def make_repo(root):
    os.makedirs(os.path.join(root, ".git"))


def make_session(repo_root, sid="s1", task="fix-thing", status="work"):
    return {"sid": sid, "pid": None, "cwd": repo_root, "root": repo_root,
            "repo": os.path.basename(repo_root) or "?", "task": task, "title": "",
            "stage": "implement", "persona": "NEO", "pglyph": "●", "mood": "action", "model": "sonnet/medium",
            "iteration": "0", "max_iter": "2", "plan_verdict": None, "diff_verdict": None, "branch": None,
            "gate": "", "dejavu": False, "status": status, "now": "▶ working", "text": "", "cost": 0.1,
            "ctx_pct": 10, "ctx_tokens": None, "lines": (1, 1), "start": time.time(), "last_seen": time.time(),
            "agents": (0, 0, ""), "idle": False, "transcript_path": None, "tmux_pane": None, "tmux_addr": None,
            "shipped": False, "hb_ts": None, "hidden": False}


class TestWorkspaceScan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        make_repo(os.path.join(self.tmp, "claude-loop"))
        os.makedirs(os.path.join(self.tmp, "autoretouch"))
        make_repo(os.path.join(self.tmp, "autoretouch", "ai-shoot-service"))
        make_repo(os.path.join(self.tmp, "autoretouch", "fashion-webapp-2"))
        fleet._WS_CACHE.clear()

    def names(self):
        fleet._WS_CACHE.clear()
        return [e["name"] for e in fleet.scan_workspace(self.tmp)]

    def test_scan_is_flat_with_dir_prefixes(self):
        self.assertEqual(self.names(), ["autoretouch/ai-shoot-service", "autoretouch/fashion-webapp-2", "claude-loop"])

    def test_scan_reaches_two_plain_dirs_deep(self):
        make_repo(os.path.join(self.tmp, "autoretouch", "mpe", "watermark"))
        os.makedirs(os.path.join(self.tmp, "autoretouch", "mpe", "not-a-repo", "deeper"))
        make_repo(os.path.join(self.tmp, "a", "b", "c", "too-deep"))
        names = self.names()
        self.assertIn("autoretouch/mpe/watermark", names)
        self.assertFalse(any("too-deep" in n for n in names))

    def test_scan_sees_a_submodule_whose_dot_git_is_a_file(self):
        """A submodule writes `.git` as a file. It is still a repo."""
        sub = os.path.join(self.tmp, "ar-core-eval")
        os.makedirs(sub)
        with open(os.path.join(sub, ".git"), "w") as fh:
            fh.write("gitdir: ../claude-loop/.git/modules/ar-core-eval\n")
        self.assertIn("ar-core-eval", self.names())
        self.assertEqual(fleet.workspace_root(sub), self.tmp)

    def test_a_linked_worktree_is_not_a_repo_and_its_session_counts_under_the_main_checkout(self):
        wt = os.path.join(self.tmp, "claude-loop-wt")
        os.makedirs(wt)
        with open(os.path.join(wt, ".git"), "w") as fh:
            fh.write(f"gitdir: {self.tmp}/claude-loop/.git/worktrees/claude-loop-wt\n")
        self.assertNotIn("claude-loop-wt", self.names())
        rows = fleet.ws_rows([make_session(wt, sid="wt")], self.tmp)
        self.assertEqual(next(r for r in rows if r["repo"] == "claude-loop")["now"], "1 agent")

    def test_workspace_root_steps_one_level_up_from_a_repo(self):
        self.assertEqual(fleet.workspace_root(os.path.join(self.tmp, "claude-loop")), self.tmp)

    def test_workspace_root_is_cwd_with_no_repo_anywhere(self):
        with tempfile.TemporaryDirectory() as bare:
            self.assertEqual(fleet.workspace_root(bare), bare)

    def test_sessions_first_then_the_repos_section(self):
        sess = [make_session(os.path.join(self.tmp, "claude-loop")),
                make_session("/somewhere/else", sid="s3")]
        rows = fleet.ws_rows(sess, self.tmp)
        self.assertEqual(rows[:2], sess)                                  # sessions untouched, on top
        self.assertEqual(rows[2]["kind"], "section")
        self.assertEqual([r["repo"] for r in rows[3:]],
                         ["autoretouch/ai-shoot-service", "autoretouch/fashion-webapp-2", "claude-loop"])
        self.assertTrue(all(r["kind"] == "repo" for r in rows[3:]))

    def test_folded_section_is_one_line(self):
        rows = fleet.ws_rows([make_session(self.tmp)], self.tmp, folded=True)
        self.assertEqual([r.get("kind") for r in rows], [None, "section"])

    def test_no_repos_returns_sessions_verbatim_and_still_filters(self):
        with tempfile.TemporaryDirectory() as bare:
            sess = [make_session(bare, task="alpha"), make_session(bare, sid="s2", task="beta")]
            self.assertEqual(fleet.ws_rows(sess, bare), sess)
            self.assertEqual(fleet.ws_rows(sess, bare, "alpha"), [sess[0]])

    def test_filter_applies_to_sessions_and_repos(self):
        sess = [make_session(os.path.join(self.tmp, "claude-loop"), task="alpha")]
        rows = fleet.ws_rows(sess, self.tmp, "shoot")
        self.assertEqual([r["repo"] for r in rows if r.get("kind") == "repo"], ["autoretouch/ai-shoot-service"])
        self.assertNotIn("s1", [r["sid"] for r in rows])

    def test_hidden_repo_leaves_the_list_its_sessions_stay(self):
        sess = [make_session(os.path.join(self.tmp, "claude-loop"))]
        rows = fleet.ws_rows(sess, self.tmp, hidden={"claude-loop"})
        self.assertIn("s1", [r["sid"] for r in rows])                    # a live agent is never hidden by its repo
        self.assertNotIn("claude-loop", [r["repo"] for r in rows if r.get("kind") == "repo"])
        shown = fleet.ws_rows(sess, self.tmp, hidden={"claude-loop"}, show_hidden=True)
        self.assertTrue(next(r for r in shown if r.get("kind") == "repo" and r["repo"] == "claude-loop")["hidden"])

    def test_a_hidden_dir_hides_every_repo_under_it(self):
        """Hides saved by the old tree were group names: `autoretouch` must still hide its repos."""
        rows = fleet.ws_rows([], self.tmp, hidden={"autoretouch"})
        self.assertEqual([r["repo"] for r in rows if r.get("kind") == "repo"], ["claude-loop"])

    def test_long_dead_sessions_fold_into_one_line(self):
        repo = os.path.join(self.tmp, "claude-loop")
        now = time.time()
        live, fresh_dead, old_dead = (make_session(repo, sid="live"), make_session(repo, sid="d1", status="sentinel"),
                                      make_session(repo, sid="d2", status="sentinel"))
        old_dead["last_seen"] = now - fleet.DEAD_FOLD_S - 1
        rows = fleet.ws_rows([live, fresh_dead, old_dead], self.tmp, now=now)
        sids = [r["sid"] for r in rows]
        self.assertEqual(sids[:3], ["live", "d1", "section:dead"])          # a fresh death is still news
        self.assertNotIn("d2", sids)
        self.assertEqual(rows[2]["repo"], "dead (1)")
        opened = [r["sid"] for r in fleet.ws_rows([live, fresh_dead, old_dead], self.tmp, dead_open=True, now=now)]
        self.assertEqual(opened[:4], ["live", "d1", "section:dead", "d2"])
        self.assertNotIn("section:dead", [r["sid"] for r in fleet.ws_rows([live], self.tmp, now=now)])
        closed = {**fresh_dead, "ended": True}                               # you exited it: history at once
        self.assertNotIn("d1", [r["sid"] for r in fleet.ws_rows([live, closed], self.tmp, now=now)])

    def test_spawned_row_is_the_new_session_in_that_repo(self):
        repo = os.path.realpath(os.path.join(self.tmp, "claude-loop"))
        old, other, new = make_session(repo, sid="old"), make_session("/elsewhere", sid="x"), make_session(repo, sid="new")
        self.assertEqual(fleet.spawned_row([old, other, new], repo, {"old"})["sid"], "new")
        self.assertIsNone(fleet.spawned_row([old, other], repo, {"old"}))

    def test_hides_matches_what_ws_rows_hides(self):
        """`b` unhides by the same rule ws_rows hides by, or an old `x` hide could never be undone."""
        for h in ("autoretouch", "ai-shoot-service", "autoretouch/ai-shoot-service"):
            self.assertTrue(fleet.hides(h, "autoretouch/ai-shoot-service"), h)
        self.assertFalse(fleet.hides("shoot-service", "autoretouch/ai-shoot-service"))

    def test_repo_rows_count_live_agents_not_sentinels(self):
        repo = os.path.join(self.tmp, "claude-loop")
        sess = [make_session(repo), make_session(repo, sid="s2"), make_session(repo, sid="d", status="sentinel")]
        row = next(r for r in fleet.ws_rows(sess, self.tmp) if r.get("kind") == "repo" and r["repo"] == "claude-loop")
        self.assertEqual(row["now"], "2 agents")

    def test_repo_row_carries_every_session_key(self):
        repo_row = next(r for r in fleet.ws_rows([], self.tmp) if r.get("kind") == "repo")
        session_keys = set(make_session(self.tmp).keys())
        self.assertTrue(session_keys <= set(repo_row.keys()), session_keys - set(repo_row.keys()))

    def test_header_counts_sessions_only(self):
        ring = make_session(os.path.join(self.tmp, "claude-loop"), sid="r1", status="ring")
        dead = make_session(os.path.join(self.tmp, "claude-loop"), sid="d1", status="sentinel")
        rows = fleet.ws_rows([ring, dead], self.tmp)
        hdr = next(ln for kind, ln in fleet.render(rows, 100, all_rows=[ring, dead]) if kind == "hdr")
        self.assertIn("1 ringing", hdr)
        self.assertIn("1 sentinel", hdr)
        self.assertIn("1 jacked in", hdr)                                  # repo rows are not sessions

    def test_repo_names_are_not_squeezed_into_the_repo_column(self):
        long = "autoretouch/a-repo-with-a-rather-long-name"
        make_repo(os.path.join(self.tmp, long))
        fleet._WS_CACHE.clear()
        lines = [ln for _, ln in fleet.render(fleet.ws_rows([], self.tmp), 120)]
        self.assertTrue(any(long in ln for ln in lines))


class TestWsPrefs(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.mkdtemp()
        self.old = fleet.FLEET_DIR, fleet.PREFS_FILE
        fleet.FLEET_DIR = self.tmp_home
        fleet.PREFS_FILE = os.path.join(self.tmp_home, "prefs.json")

    def tearDown(self):
        fleet.FLEET_DIR, fleet.PREFS_FILE = self.old

    def test_roundtrip_is_additive_and_per_workspace(self):
        self.assertEqual(fleet.ws_prefs("/ws/a"), {"hidden": [], "folded": False})
        fleet.save_ws_prefs("/ws/a", hidden=["b"])
        fleet.save_ws_prefs("/ws/a", folded=True)
        self.assertEqual(fleet.ws_prefs("/ws/a"), {"hidden": ["b"], "folded": True})
        self.assertEqual(fleet.ws_prefs("/ws/other"), {"hidden": [], "folded": False})
        fleet.save_prefs(theme="zion")                            # an unrelated pref write never wipes it
        self.assertEqual(fleet.ws_prefs("/ws/a"), {"hidden": ["b"], "folded": True})

    def test_malformed_values_are_ignored_not_fatal(self):
        import json
        json.dump({"workspaces": "not-a-dict"}, open(fleet.PREFS_FILE, "w"))
        self.assertEqual(fleet.ws_prefs("/ws/a"), {"hidden": [], "folded": False})
        json.dump({"workspaces": {"/ws/a": "junk"}}, open(fleet.PREFS_FILE, "w"))
        self.assertEqual(fleet.ws_prefs("/ws/a"), {"hidden": [], "folded": False})

    def test_old_tree_prefs_keep_their_hides(self):
        import json
        json.dump({"workspaces": {"/ws/a": {"order": ["x"], "collapsed": ["g"], "hidden": ["g"]}}}, open(fleet.PREFS_FILE, "w"))
        self.assertEqual(fleet.ws_prefs("/ws/a"), {"hidden": ["g"], "folded": False})


class TestResumeGuard(unittest.TestCase):
    def test_resume_cmd_rejects_synthetic_rows(self):
        self.assertIsNone(fleet.resume_cmd({"kind": "repo", "sid": "repo:/Users/x/repo", "cwd": "/x"}))
        self.assertIsNone(fleet.resume_cmd({"kind": "section", "sid": "section:repos", "cwd": "/x"}))

    def test_resume_cmd_still_works_for_a_real_session(self):
        self.assertEqual(fleet.resume_cmd({"sid": "8596c744-4f19-48ac-ac12-7f4445578e3d", "cwd": "/x"}),
                         "claude --resume 8596c744-4f19-48ac-ac12-7f4445578e3d")


class TestSpawn(unittest.TestCase):
    def test_slug_prefers_an_issue_id(self):
        self.assertEqual(fleet.slug("LIN-482 fix the thing"), "lin-482")

    def test_slug_falls_back_to_slugified_words_then_time(self):
        self.assertEqual(fleet.slug("Fix the Lightbox Flicker!!"), "fix-the-lightbox-flicker")
        self.assertEqual(fleet.slug(""), "task-" + time.strftime("%H%M"))

    def test_slug_never_contains_colon_or_dot(self):
        self.assertNotIn(":", fleet.slug("weird: prompt. text"))
        self.assertNotIn(".", fleet.slug("weird: prompt. text"))

    def test_spawn_cmd_on_a_repo_row_uses_the_repo_path(self):
        row = {"kind": "repo", "repo": "core-service", "path": "/ws/core-service", "ws": "/ws"}
        cwd, cmd, window = fleet.spawn_cmd(row, "LIN-482 fix it", "a")
        self.assertEqual(cwd, "/ws/core-service")
        self.assertIn("/anderson:start lin-482 LIN-482 fix it", cmd)
        self.assertEqual(window, "core-service:lin-482")

    def test_spawn_cmd_plain_mode_sends_the_prompt_verbatim(self):
        row = {"kind": "repo", "repo": "x", "path": "/ws/x", "ws": "/ws"}
        _, cmd, _ = fleet.spawn_cmd(row, "just do it", "p")
        self.assertEqual(cmd, "claude 'just do it'")

    def test_spawn_cmd_empty_prompt_is_a_bare_claude(self):
        row = {"kind": "repo", "repo": "x", "path": "/ws/x", "ws": "/ws"}
        cwd, cmd, window = fleet.spawn_cmd(row, "", "p")
        self.assertEqual((cmd, window), ("claude", "x"))

    def test_launch_agent_without_claude_on_path_says_so(self):
        old = fleet.shutil.which
        fleet.shutil.which = lambda name: None
        try:
            row = {"kind": "repo", "repo": "x", "path": "/ws/x", "ws": "/ws"}
            self.assertIn("not on PATH", fleet.launch_agent(row, "hi", "p"))
        finally:
            fleet.shutil.which = old

    def _real_repo(self, branch):
        """A real git repo with one commit, parked on `branch`. git itself, not a mock: the whole
        point of worktree_for() is what git actually does with a repo that has work in progress."""
        tmp = tempfile.mkdtemp()
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@t"}
        run = lambda *a: subprocess.run(["git", "-C", tmp, *a], capture_output=True, env=env, check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", tmp], capture_output=True, check=True)
        pathlib.Path(tmp, "f").write_text("x")
        run("add", "f"); run("commit", "-qm", "one")
        if branch != "main":
            run("checkout", "-qb", branch)
        return tmp

    def test_spawn_into_a_repo_on_a_feature_branch_gets_its_own_worktree(self):
        repo = self._real_repo("wip/someone-elses-work")
        cwd, note = fleet.worktree_for(repo, "lin-482")
        self.assertEqual(cwd, os.path.join(repo, ".worktrees", "lin-482"))
        self.assertTrue(os.path.isdir(cwd))
        self.assertEqual(fleet._git(["rev-parse", "--abbrev-ref", "HEAD"], cwd), "anderson/lin-482")
        self.assertIn("anderson/lin-482", note)
        # the repo someone was working in is untouched
        self.assertEqual(fleet._git(["rev-parse", "--abbrev-ref", "HEAD"], repo), "wip/someone-elses-work")
        # and a second spawn under the same task reuses it instead of failing
        again, note2 = fleet.worktree_for(repo, "lin-482")
        self.assertEqual(again, cwd)
        self.assertIn("reused", note2)

    def test_spawn_into_a_repo_on_its_default_branch_uses_the_checkout_itself(self):
        repo = self._real_repo("main")
        self.assertEqual(fleet.worktree_for(repo, "lin-482"), (repo, ""))

    def test_worktree_for_a_plain_directory_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as plain:
            self.assertEqual(fleet.worktree_for(plain, "x"), (plain, ""))

    def test_an_agent_in_a_worktree_still_rows_under_its_repo(self):
        ws = tempfile.mkdtemp()
        repo = os.path.join(ws, "claude-loop")
        make_repo(repo)
        for wt in (os.path.join(repo, ".worktrees", "lin-482"), os.path.join(repo, ".claude", "worktrees", "x+y")):
            os.makedirs(wt)
            with open(os.path.join(wt, ".git"), "w") as fh:
                fh.write(f"gitdir: {repo}/.git/worktrees/{os.path.basename(wt)}\n")
        fleet._WS_CACHE.clear()
        sess = [make_session(os.path.join(repo, ".worktrees", "lin-482"), sid="wt"),
                make_session(os.path.join(repo, ".claude", "worktrees", "x+y"), sid="cc")]   # Claude Code's own
        self.assertEqual({fleet.session_root(s) for s in sess}, {os.path.realpath(repo)})
        row = next(r for r in fleet.ws_rows(sess, ws) if r.get("kind") == "repo" and r["repo"] == "claude-loop")
        self.assertEqual(row["now"], "2 agents")

    def test_launch_agent_never_replaces_the_fleet_window(self):
        """The monitor has to survive a spawn: on macOS the agent gets its own OS tab even under
        tmux, and the tmux fallback elsewhere creates the window with -d so focus stays on fleet."""
        row = {"kind": "repo", "repo": "x", "path": "/ws/x", "ws": "/ws"}
        old_tmux = os.environ.get("TMUX")
        os.environ["TMUX"] = "/tmp/tmux-0/default,123,0"
        seen = []

        def fake_run(args, *a, **k):
            seen.append(args)
            return subprocess.CompletedProcess(args, 0, "", "")

        try:
            with mock.patch.object(fleet.subprocess, "run", side_effect=fake_run), \
                 mock.patch.object(fleet.shutil, "which", side_effect=lambda n: "/usr/bin/" + n), \
                 mock.patch.object(fleet.sys, "platform", "linux"):
                fleet.launch_agent(row, "hi", "p")
            self.assertEqual(next(a for a in seen if a[0] == "tmux")[:3], ["tmux", "new-window", "-d"])

            seen.clear()
            with mock.patch.object(fleet.subprocess, "run", side_effect=fake_run), \
                 mock.patch.object(fleet.shutil, "which", side_effect=lambda n: "/usr/bin/" + n), \
                 mock.patch.object(fleet.sys, "platform", "darwin"):
                fleet.launch_agent(row, "hi", "p")
            self.assertNotIn("tmux", [a[0] for a in seen])              # a real window, not a tmux one
            self.assertIn("osascript", [a[0] for a in seen])
        finally:
            if old_tmux is None:
                os.environ.pop("TMUX", None)
            else:
                os.environ["TMUX"] = old_tmux

    def test_new_terminal_opens_a_tab_in_the_host_terminal(self):
        """Spawned from Ghostty (even under tmux, where TERM_PROGRAM=tmux) -> a new Ghostty tab, not
        Terminal.app. iTerm2 -> an iTerm2 tab. Anything else keeps the Terminal.app window."""
        cases = [({"__CFBundleIdentifier": "com.mitchellh.ghostty", "TERM_PROGRAM": "tmux"}, 'application "Ghostty"', "Ghostty tab"),
                 ({"TERM_PROGRAM": "ghostty"}, 'application "Ghostty"', "Ghostty tab"),
                 ({"__CFBundleIdentifier": "com.googlecode.iterm2"}, "create tab", "iTerm2 tab"),
                 ({"TERM_PROGRAM": "Apple_Terminal"}, 'application "Terminal"', "Terminal window")]
        for env, want, msg in cases:
            seen = []
            clean = {k: v for k, v in os.environ.items() if k not in ("TMUX", "TERM_PROGRAM", "__CFBundleIdentifier")}
            with mock.patch.dict(os.environ, {**clean, **env}, clear=True), \
                 mock.patch.object(fleet.subprocess, "run", side_effect=lambda a, *x, **k: seen.append(a) or mock.Mock(returncode=0)), \
                 mock.patch.object(fleet.sys, "platform", "darwin"):
                out = fleet.new_terminal("claude", cwd="/tmp/a b", name="r:t")
            self.assertIn(want, seen[0][2], env)
            self.assertIn("cd '/tmp/a b' && claude", seen[0][2])
            self.assertIn(msg, out)
            # a Ghostty tab starts in cwd, so ghostty_pick() can find it by directory later
            self.assertEqual('initial working directory of cfg to "/tmp/a b"' in seen[0][2], "Ghostty" in msg, env)

    def test_ghostty_pick_finds_the_session_tab_by_directory(self):
        """Ghostty has no tty to match on: jack in picks the tab by working directory, and a
        claude title beats a bare shell prompt sharing that directory."""
        ls = ("A\t/ws/web\talex@mac:~/ws/web\n"
              "B\t/ws/web\t◐ Image targeting refactor\n"
              "C\t/ws/api\t✳ Claude Code\n"
              "D\t/ws/two\t✳ one\nE\t/ws/two\t◐ other\n")
        self.assertEqual(fleet.ghostty_pick(ls, "/ws/web"), ("B", None))
        self.assertEqual(fleet.ghostty_pick(ls, "/ws/api"), ("C", None))
        self.assertIsNone(fleet.ghostty_pick(ls, "/ws/two")[0])        # two claude tabs: say so, don't guess
        self.assertIsNone(fleet.ghostty_pick(ls, "/ws/none")[0])
        self.assertIsNone(fleet.ghostty_pick("", "/ws/web")[0])

    def test_ghostty_tid_splits_same_repo_tabs_by_tty_and_caches_it(self):
        """Three claude tabs in one checkout: the cwd pick can't choose, so the session's tty gets a
        unique title, the tab showing it is the one, and the old title goes back. Found once per pid."""
        tabs = {"A": "◐ one", "B": "✳ two", "C": "✳ Claude Code"}
        titles = []
        listing = lambda *a: "".join(f"{i}\t/ws/web\t{n}\n" for i, n in tabs.items())
        def title(tty, t):
            titles.append(t)
            if tty == "/dev/ttys004":
                tabs["B"] = t
        fleet._GHOSTTY_TID.clear()
        with mock.patch.object(fleet, "_ghostty_list", side_effect=listing), \
             mock.patch.object(fleet, "_tty_title", side_effect=title), \
             mock.patch.object(fleet, "_tty_of", side_effect=lambda pid: "/dev/ttys004" if pid == 7 else None):
            self.assertEqual(fleet.ghostty_tid({"pid": 7, "cwd": "/ws/web"}, 1), ("B", None))
            self.assertEqual(tabs["B"], "✳ two")                                # old title restored
            n = len(titles)
            self.assertEqual(fleet.ghostty_tid({"pid": 7, "cwd": "/ws/web"}, 1), ("B", None))
            self.assertEqual(len(titles), n)                                    # cached: no second title flash
            self.assertIn("can't tell", fleet.ghostty_tid({"pid": 8, "cwd": "/ws/web"}, 1)[1])   # no tty: cwd fallback says so

    def test_ghostty_without_tty_or_dir_does_not_guess(self):
        with mock.patch.object(fleet, "_ghostty_list", return_value="A\t" + os.getcwd() + "\tfleet\n"), \
             mock.patch.object(fleet, "_tty_of", return_value=None):
            self.assertIsNone(fleet.ghostty_tid({"pid": 10}, 1)[0])            # never fleet's own tab by accident

    def test_ghostty_fallback_uses_the_launch_dir_not_the_live_cwd(self):
        """The hook's cwd follows every `cd` the session makes; the Ghostty tab stays where claude started."""
        listing = "A\t/ws/web\t✳ Claude Code\n"
        with mock.patch.object(fleet, "_ghostty_list", return_value=listing), \
             mock.patch.object(fleet, "_tty_of", return_value=None):
            r = {"pid": 9, "cwd": "/ws/web/packages/ui", "start_cwd": "/ws/web"}
            self.assertEqual(fleet.ghostty_tid(r, 1), ("A", None))

    def test_new_terminal_tmux_failure_says_so_and_copies_to_clipboard(self):
        """criterion 5's failure half: tmux (or the launch) fails -> fleet says what failed AND
        the exact command still lands on the clipboard. mock.patch.object, not a manual
        save/assign/restore, so the real stdlib attrs are guaranteed back even if an assertion
        fails mid-test."""
        old_tmux = os.environ.get("TMUX")
        os.environ["TMUX"] = "/tmp/tmux-0/default,123,0"
        copied = {}

        def fake_run(args, *a, **k):
            if args[0] == "tmux":
                raise RuntimeError("no server running")
            copied["cmd"] = k.get("input")

        try:
            with mock.patch.object(fleet.subprocess, "run", side_effect=fake_run), \
                 mock.patch.object(fleet.sys, "platform", "linux"), \
                 mock.patch.object(fleet.shutil, "which",
                                   side_effect=lambda name: "/usr/bin/pbcopy" if name == "pbcopy" else None):
                result = fleet.new_terminal("claude --resume xyz")
                self.assertIn("launch failed", result)
                self.assertEqual(copied.get("cmd"), "claude --resume xyz")
        finally:
            if old_tmux is None:
                os.environ.pop("TMUX", None)
            else:
                os.environ["TMUX"] = old_tmux


class TestViewport(unittest.TestCase):
    def test_more_rows_than_height_keeps_footer_card_and_cursor_onscreen(self):
        rows = [dict(sid=f"b{i}", pid=None, cwd="", root="", repo=f"repo{i}", task="t", stage="implement",
                     persona="NEO", pglyph="●", mood="action", model="sonnet/medium", iteration="0", max_iter="2",
                     plan_verdict=None, diff_verdict=None, branch=None, gate="", dejavu=False, status="work",
                     now="▶ working", text="", cost=0.1, ctx_pct=10, ctx_tokens=None, lines=(1, 1),
                     start=time.time(), last_seen=time.time(), agents=(0, 0, ""), idle=False, transcript_path=None,
                     tmux_pane=None, tmux_addr=None, shipped=False, hb_ts=None, hidden=False)
                for i in range(40)]
        lines = fleet.render(rows, 100, sel=37, height=24)
        self.assertLessEqual(len(lines), 24)
        self.assertEqual(lines[-1][0], "foot")
        self.assertTrue(any(kind.endswith("_sel") for kind, _ in lines))

    def test_fits_without_windowing_when_rows_already_fit(self):
        rows = [dict(sid="a", pid=None, cwd="", root="", repo="a", task="t", stage="implement",
                     persona="NEO", pglyph="●", mood="action", model="sonnet/medium", iteration="0", max_iter="2",
                     plan_verdict=None, diff_verdict=None, branch=None, gate="", dejavu=False, status="work",
                     now="▶ working", text="", cost=0.1, ctx_pct=10, ctx_tokens=None, lines=(1, 1),
                     start=time.time(), last_seen=time.time(), agents=(0, 0, ""), idle=False, transcript_path=None,
                     tmux_pane=None, tmux_addr=None, shipped=False, hb_ts=None, hidden=False)]
        off, cnt = fleet._row_window(rows, 100, "", 24, 0)
        self.assertEqual((off, cnt), (0, 1))


class TestLauncherDefaultMode(unittest.TestCase):
    """`fleet` runs right here by default, tmux or not; only --tmux starts a session."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.stub_dir = os.path.join(self.tmp, "stubbin")
        os.makedirs(self.stub_dir)
        self.log = os.path.join(self.tmp, "tmux.log")
        with open(os.path.join(self.stub_dir, "tmux"), "w") as f:
            f.write(f'#!/usr/bin/env bash\necho "$@" >> "{self.log}"\nexit 0\n')
        os.chmod(os.path.join(self.stub_dir, "tmux"), 0o755)

    def _env(self):
        return {**os.environ, "PATH": self.stub_dir + os.pathsep + os.environ["PATH"], "TMUX": "",
                "FLEET_BIN_DIR": self.tmp}

    def test_once_always_runs_in_place_tmux_or_not(self):
        r = subprocess.run(["bash", str(BIN / "fleet"), "--once"], env=self._env(), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)   # --once always runs in place
        log = open(self.log).read() if os.path.exists(self.log) else ""
        self.assertNotIn("new-session", log)          # fleet.py itself may still probe tmux panes

    def test_default_never_starts_a_tmux_session(self):
        for args in (["--once"], ["--here", "--once"]):
            r = subprocess.run(["bash", str(BIN / "fleet"), *args], env=self._env(), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            log = open(self.log).read() if os.path.exists(self.log) else ""
            self.assertNotIn("new-session", log)

    def test_tmux_flag_starts_the_fleet_session(self):
        r = subprocess.run(["bash", str(BIN / "fleet"), "--tmux"], env=self._env(), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("new-session -A -s fleet", open(self.log).read())


class TestLiveCheckout(unittest.TestCase):
    def test_git_branch_reads_head_of_a_repo_and_of_a_linked_worktree(self):
        tmp = tempfile.mkdtemp()
        repo, wt = os.path.join(tmp, "r"), os.path.join(tmp, "r", ".claude", "worktrees", "w")
        os.makedirs(os.path.join(repo, ".git", "worktrees", "w")); os.makedirs(wt)
        pathlib.Path(repo, ".git", "HEAD").write_text("ref: refs/heads/main\n")
        pathlib.Path(repo, ".git", "worktrees", "w", "HEAD").write_text("ref: refs/heads/me/feature\n")
        pathlib.Path(wt, ".git").write_text("gitdir: ../../../.git/worktrees/w\n")      # relative, git >= 2.48
        self.assertEqual(fleet.git_branch(repo), "main")
        self.assertEqual(fleet.git_branch(wt), "me/feature")              # the worktree's, not the transcript's
        self.assertEqual(fleet.worktree_main(wt), os.path.realpath(repo))
        self.assertIsNone(fleet.worktree_main(repo))
        self.assertIsNone(fleet.git_branch(tmp))

    def test_a_shipped_row_renders_in_its_own_kind(self):
        rows = [make_session("/ws/a", sid="done"), make_session("/ws/b", sid="live")]
        rows[0]["shipped"] = True
        kinds = [k for k, _ in fleet.render(rows, 150, sel=1)]
        top = kinds.index("colhdr") + 1
        self.assertEqual(kinds[top:top + 2], ["shipped", "work_sel"])


if __name__ == "__main__":
    unittest.main()
