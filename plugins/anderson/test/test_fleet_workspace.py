"""fleet.py workspace mode (phases 1+2): repo/group tree rows, per-workspace J/K + collapse,
the row viewport, and the ⏎ -> prompt -> p/a/A spawn flow. Loads bin/fleet.py by path, same
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

    def test_scan_finds_direct_repos_and_nested_groups(self):
        scan = fleet.scan_workspace(self.tmp)
        by_name = {e["name"]: e for e in scan}
        self.assertEqual(by_name["claude-loop"]["kind"], "repo")
        self.assertEqual(by_name["autoretouch"]["kind"], "group")
        self.assertEqual({r["name"] for r in by_name["autoretouch"]["repos"]},
                          {"ai-shoot-service", "fashion-webapp-2"})

    def test_workspace_root_steps_one_level_up_from_a_repo(self):
        self.assertEqual(fleet.workspace_root(os.path.join(self.tmp, "claude-loop")), self.tmp)

    def test_workspace_root_is_cwd_with_no_repo_anywhere(self):
        with tempfile.TemporaryDirectory() as bare:
            self.assertEqual(fleet.workspace_root(bare), bare)

    def test_tree_rows_nests_repos_groups_and_elsewhere(self):
        sess = [make_session(os.path.join(self.tmp, "claude-loop")),
                make_session(os.path.join(self.tmp, "autoretouch", "ai-shoot-service"), sid="s2"),
                make_session("/somewhere/else", sid="s3")]
        rows = fleet.tree_rows(sess, self.tmp, "", set())
        kinds = [(r.get("kind"), r["repo"]) for r in rows]
        self.assertIn(("repo", "claude-loop"), kinds)
        self.assertIn(("group", "autoretouch"), kinds)
        self.assertIn(("group", "elsewhere"), kinds)
        # sessions matched to their repo/group are interleaved, unchanged but for the display
        # indent that nests them under their repo/group row
        self.assertIn({**sess[0], "indent": 1}, rows)
        self.assertIn({**sess[1], "indent": 2}, rows)
        self.assertIn({**sess[2], "indent": 1}, rows)

    def test_no_repos_under_launch_dir_returns_sessions_verbatim(self):
        with tempfile.TemporaryDirectory() as bare:
            sess = [make_session(bare)]
            self.assertEqual(fleet.tree_rows(sess, bare, "", set()), sess)

    def test_no_repos_fallback_still_filters(self):
        with tempfile.TemporaryDirectory() as bare:
            sess = [make_session(bare, task="alpha"), make_session(bare, sid="s2", task="beta")]
            self.assertEqual(fleet.tree_rows(sess, bare, "alpha", set()), [sess[0]])

    def test_hidden_repo_takes_its_sessions_with_it_and_does_not_leak_into_elsewhere(self):
        sess = [make_session(os.path.join(self.tmp, "claude-loop")),
                make_session(os.path.join(self.tmp, "autoretouch", "ai-shoot-service"), sid="s2")]
        rows = fleet.tree_rows(sess, self.tmp, "", set(), (), {"claude-loop"})
        self.assertNotIn("claude-loop", [r["repo"] for r in rows])
        self.assertNotIn(sess[0]["sid"], [r["sid"] for r in rows])       # not re-homed under `elsewhere`
        self.assertNotIn("elsewhere", [r["repo"] for r in rows])
        self.assertIn("s2", [r["sid"] for r in rows])                    # the other repo is untouched

    def test_hidden_group_hides_its_repos_too_and_show_hidden_lists_it_folded(self):
        rows = fleet.tree_rows([], self.tmp, "", set(), (), {"autoretouch"})
        names = [r["repo"] for r in rows]
        self.assertNotIn("autoretouch", names)
        self.assertNotIn("ai-shoot-service", names)
        rows = fleet.tree_rows([], self.tmp, "", set(), (), {"autoretouch"}, show_hidden=True)
        grp = next(r for r in rows if r["repo"] == "autoretouch")
        self.assertTrue(grp["hidden"])                                   # dim, flagged, and `b` un-hides it
        self.assertTrue(grp["collapsed"])
        self.assertNotIn("ai-shoot-service", [r["repo"] for r in rows])  # revealed folded, not expanded

    def test_collapsed_group_hides_its_repos_but_keeps_its_summary(self):
        sess = [make_session(os.path.join(self.tmp, "autoretouch", "ai-shoot-service"), status="ring")]
        rows = fleet.tree_rows(sess, self.tmp, "", {"autoretouch"})
        names = [r["repo"] for r in rows]
        self.assertIn("autoretouch", names)
        self.assertNotIn("ai-shoot-service", names)              # collapsed: repo row not emitted
        grp = next(r for r in rows if r["repo"] == "autoretouch")
        self.assertIn("ringing", grp["now"])                      # rolled-up summary survives collapse
        self.assertEqual(grp["status"], "ring")                   # Q12: reuses the ring-pulse path

    def test_repo_row_carries_every_session_key(self):
        rows = fleet.tree_rows([], self.tmp, "", set())
        repo_row = next(r for r in rows if r.get("kind") == "repo")
        session_keys = set(make_session(self.tmp).keys())
        self.assertTrue(session_keys <= set(repo_row.keys()), session_keys - set(repo_row.keys()))

    def test_header_counts_the_full_session_list_not_just_the_visible_tree(self):
        """render()'s aggregates must still read as SESSIONS: a ring hidden under a collapsed
        group must still show in the header, same as a `discover()`-only flat list would."""
        ring = make_session(os.path.join(self.tmp, "autoretouch", "ai-shoot-service"), sid="r1", status="ring")
        dead = make_session(os.path.join(self.tmp, "claude-loop"), sid="d1", status="sentinel")
        all_rows = [ring, dead]
        rows = fleet.tree_rows(all_rows, self.tmp, "", {"autoretouch"})   # ring's repo is collapsed away
        self.assertNotIn("r1", [r["sid"] for r in rows])                 # sanity: really hidden from `rows`
        hdr = next(ln for kind, ln in fleet.render(rows, 100, all_rows=all_rows) if kind == "hdr")
        self.assertIn("1 ringing", hdr)
        self.assertIn("1 sentinel", hdr)
        self.assertIn("1 jacked in", hdr)


class TestReorderHandler(unittest.TestCase):
    """`move_ws_row()` is the pure core the `J`/`K` handler calls -- exercised directly here so a
    reorder bug isn't only provable through `save_ws_prefs()`'s own round-trip test."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        for name in ("aa", "bb", "cc", "dd"):
            make_repo(os.path.join(self.tmp, name))
        fleet._WS_CACHE.clear()

    def test_two_consecutive_j_presses_move_a_repo_two_slots_and_cursor_follows_it(self):
        order, collapsed = [], set()
        rows = fleet.tree_rows([], self.tmp, "", collapsed, order)
        sel = next(i for i, r in enumerate(rows) if r["repo"] == "aa")
        order, sid = fleet.move_ws_row(rows, sel, True, order)          # J: aa <-> bb
        rows = fleet.tree_rows([], self.tmp, "", collapsed, order)
        sel = next(i for i, r in enumerate(rows) if r["sid"] == sid)
        order, sid = fleet.move_ws_row(rows, sel, True, order)          # J again: aa <-> cc
        rows = fleet.tree_rows([], self.tmp, "", collapsed, order)
        sel = next(i for i, r in enumerate(rows) if r["sid"] == sid)
        self.assertEqual([r["repo"] for r in rows if r.get("kind") == "repo"], ["bb", "cc", "aa", "dd"])
        self.assertEqual(rows[sel]["repo"], "aa")                       # cursor stayed on the moved repo

    def test_reorder_under_a_collapsed_sibling_group_keeps_its_hidden_intra_group_order(self):
        """repro: grp/{aa,bb} + solo + zzz. J on aa (expanded) then, after collapsing grp, J on
        solo must not drop aa/bb from the saved order just because they're offscreen."""
        tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(tmp, "grp"))
        make_repo(os.path.join(tmp, "grp", "aa"))
        make_repo(os.path.join(tmp, "grp", "bb"))
        make_repo(os.path.join(tmp, "solo"))
        make_repo(os.path.join(tmp, "zzz"))
        fleet._WS_CACHE.clear()
        order, collapsed = [], set()
        rows = fleet.tree_rows([], tmp, "", collapsed, order)
        sel = next(i for i, r in enumerate(rows) if r["repo"] == "aa")
        order, _ = fleet.move_ws_row(rows, sel, True, order)             # J: aa <-> bb (grp expanded)
        self.assertEqual(order, ["grp", "bb", "aa", "solo", "zzz"])
        collapsed.add("grp")
        rows = fleet.tree_rows([], tmp, "", collapsed, order)
        self.assertNotIn("aa", [r["repo"] for r in rows])                # now hidden by the collapse
        sel = next(i for i, r in enumerate(rows) if r["repo"] == "solo")
        order, _ = fleet.move_ws_row(rows, sel, True, order)              # J: solo <-> zzz
        self.assertEqual(order, ["grp", "bb", "aa", "zzz", "solo"])       # aa/bb survive the reorder


    def test_reorder_onto_the_elsewhere_row_is_refused_not_a_crash(self):
        """`elsewhere` is synthetic and never in `scan_workspace()`, so a naive `names.index()`
        raises ValueError -- uncaught, that kills the TUI. Both triggers are one keypress away
        whenever a session lives outside the workspace."""
        outside = [make_session("/somewhere/else", sid="x1")]
        rows = fleet.tree_rows(outside, self.tmp, "", set(), [])
        self.assertEqual(rows[-2]["repo"], "elsewhere")                  # sanity: the row is on screen
        sel = next(i for i, r in enumerate(rows) if r["repo"] == "elsewhere")
        self.assertEqual(fleet.move_ws_row(rows, sel, False, []), (None, None))   # K on elsewhere
        last = max(i for i, r in enumerate(rows) if r.get("kind") == "repo")
        self.assertEqual(fleet.move_ws_row(rows, last, True, []), (None, None))   # J onto elsewhere
        first = next(i for i, r in enumerate(rows) if r.get("kind") == "repo")
        self.assertIsNotNone(fleet.move_ws_row(rows, first, True, [])[0])          # real rows still move


class TestOrderAndCollapsePrefs(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.mkdtemp()
        self.old = fleet.FLEET_DIR, fleet.PREFS_FILE
        fleet.FLEET_DIR = self.tmp_home
        fleet.PREFS_FILE = os.path.join(self.tmp_home, "prefs.json")

    def tearDown(self):
        fleet.FLEET_DIR, fleet.PREFS_FILE = self.old

    def test_ws_prefs_roundtrip_is_additive_and_per_workspace(self):
        self.assertIsNone(fleet.ws_prefs("/ws/a"))
        fleet.save_ws_prefs("/ws/a", order=["b", "a"], collapsed=["b"])
        self.assertEqual(fleet.ws_prefs("/ws/a"), {"order": ["b", "a"], "collapsed": ["b"], "hidden": []})
        self.assertIsNone(fleet.ws_prefs("/ws/other"))            # a different workspace keeps its own
        fleet.save_prefs(theme="zion")                            # an unrelated pref write never wipes it
        self.assertEqual(fleet.ws_prefs("/ws/a"), {"order": ["b", "a"], "collapsed": ["b"], "hidden": []})

    def test_malformed_workspaces_value_is_ignored_not_fatal(self):
        import json
        json.dump({"workspaces": "not-a-dict"}, open(fleet.PREFS_FILE, "w"))
        self.assertEqual(fleet.load_prefs()["workspaces"], {})
        self.assertIsNone(fleet.ws_prefs("/ws/a"))                # never crashes on a hand-edited file

    def test_ws_prefs_coerces_a_non_dict_per_workspace_entry(self):
        # {"<ws>": "junk"} used to AttributeError in run_tui() on wprefs.get(...)
        import json
        json.dump({"workspaces": {"/ws/a": "junk"}}, open(fleet.PREFS_FILE, "w"))
        self.assertIsNone(fleet.ws_prefs("/ws/a"))

    def test_ws_prefs_fills_a_missing_collapsed_key(self):
        # {"<ws>": {"order": []}} (no "collapsed") used to KeyError on --once's saved["collapsed"]
        import json
        json.dump({"workspaces": {"/ws/a": {"order": ["x"]}}}, open(fleet.PREFS_FILE, "w"))
        self.assertEqual(fleet.ws_prefs("/ws/a"), {"order": ["x"], "collapsed": [], "hidden": []})

    def test_apply_order_unseen_names_appended_alphabetically(self):
        self.assertEqual(fleet._apply_order(["z", "a", "b"], ["b", "z"]), ["b", "z", "a"])

    def test_apply_order_drops_a_name_no_longer_in_the_scan(self):
        # "gone" is only in the saved order, not in `names` (repo deleted): it must not reappear
        self.assertEqual(fleet._apply_order(["z", "a"], ["gone", "b", "z"]), ["z", "a"])


class TestResumeGuard(unittest.TestCase):
    """resume_cmd() is the shared choke point for `c`, copy_resume() and revive(): a synthetic
    repo:/group: sid must never reach the clipboard (criterion 5)."""

    def test_resume_cmd_rejects_synthetic_rows(self):
        self.assertIsNone(fleet.resume_cmd({"kind": "repo", "sid": "repo:/Users/x/repo", "cwd": "/x"}))
        self.assertIsNone(fleet.resume_cmd({"kind": "group", "sid": "group:autoretouch", "cwd": "/x"}))

    def test_resume_cmd_still_works_for_a_real_session(self):
        cmd = fleet.resume_cmd({"sid": "8596c744-4f19-48ac-ac12-7f4445578e3d", "cwd": "/x"})
        self.assertIn("claude --resume", cmd)

    def test_copy_resume_on_a_synthetic_row_says_no_session_id(self):
        self.assertEqual(fleet.copy_resume({"kind": "group", "sid": "group:g", "cwd": "/x"}),
                          "no session id for that row.")


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

    def test_spawn_cmd_on_a_group_row_uses_the_workspace_root(self):
        row = {"kind": "group", "repo": "autoretouch", "path": "/ws/autoretouch", "ws": "/ws"}
        cwd, cmd, window = fleet.spawn_cmd(row, "sweep the fleet", "A")
        self.assertEqual(cwd, "/ws")
        self.assertIn("/anderson:auto sweep-the-fleet sweep the fleet", cmd)

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

    def test_launch_agent_never_replaces_the_fleet_window(self):
        """The monitor has to survive a spawn: on macOS the agent gets its own OS window, and the
        tmux fallback creates the window with -d so focus stays on fleet."""
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
            self.assertEqual(seen[0][:3], ["tmux", "new-window", "-d"])

            seen.clear()
            with mock.patch.object(fleet.subprocess, "run", side_effect=fake_run), \
                 mock.patch.object(fleet.shutil, "which", side_effect=lambda n: "/usr/bin/" + n), \
                 mock.patch.object(fleet.sys, "platform", "darwin"):
                fleet.launch_agent(row, "hi", "p")
            self.assertEqual(seen[0][0], "osascript")                   # a real window, not a tmux one
        finally:
            if old_tmux is None:
                os.environ.pop("TMUX", None)
            else:
                os.environ["TMUX"] = old_tmux

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


class TestPopOut(unittest.TestCase):
    def test_pop_out_cmds_groups_by_the_panes_own_session_not_fleets(self):
        cmds = fleet.pop_out_cmds("someone-elses-session", "3")
        self.assertEqual(cmds["grouped"], "fleet-pop-someone-elses-session")
        self.assertEqual(cmds["new_session"], ["tmux", "new-session", "-d", "-s", "fleet-pop-someone-elses-session",
                                                "-t", "someone-elses-session"])
        self.assertEqual(cmds["select_window"], ["tmux", "select-window", "-t", "fleet-pop-someone-elses-session:3"])
        self.assertIn("fleet-pop-someone-elses-session", cmds["attach"])

    def test_pop_out_cmds_strips_colon_and_dot_from_the_grouped_name(self):
        cmds = fleet.pop_out_cmds("core-service:LIN-482", "1")
        self.assertNotIn(":", cmds["grouped"])
        self.assertNotIn(".", cmds["grouped"])

    def test_pop_out_without_a_tmux_pane_says_so(self):
        self.assertEqual(fleet.pop_out({"tmux_pane": None}), "no tmux pane for that row.")

    def test_pop_out_twice_reuses_the_pop_session_instead_of_leaking_one(self):
        """A second `D` on the same row: grouped sessions share windows, so tmux resolves the
        pane's #S to the pop session itself (already `fleet-pop-...`). Must group against that
        directly, never re-prefix it (which grows the name and defeats the has-session guard)."""
        calls = []

        class Ok:
            returncode = 0
            stdout = "fleet-pop-abc 3"

        def fake_run(args, *a, **k):
            calls.append(args)
            return Ok()

        with mock.patch.object(fleet.subprocess, "run", side_effect=fake_run):
            fleet.pop_out({"tmux_pane": "%3"})
        joined = [" ".join(c) for c in calls if isinstance(c, list)]
        self.assertTrue(any(c == ["tmux", "has-session", "-t", "fleet-pop-abc"] for c in calls))
        self.assertFalse(any("fleet-pop-fleet-pop" in j for j in joined))            # no re-prefix
        self.assertFalse(any(c[:2] == ["tmux", "new-session"] for c in calls))       # already exists: no leak


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
    """`fleet` outside tmux now attaches a per-workspace tmux session by default; `--here` still
    runs in place; no tmux -> nothing changes."""

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

    def test_default_outside_tmux_attaches_a_per_workspace_session(self):
        """No args, outside tmux: the launcher itself starts a per-workspace tmux session (the
        stub tmux only logs and exits, so this never blocks on a real curses TUI)."""
        r = subprocess.run(["bash", str(BIN / "fleet")], env=self._env(), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("new-session -A -s fleet-", open(self.log).read())

    def test_here_flag_never_starts_a_tmux_session(self):
        r = subprocess.run(["bash", str(BIN / "fleet"), "--here", "--once"], env=self._env(),
                            capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        log = open(self.log).read() if os.path.exists(self.log) else ""
        self.assertNotIn("new-session", log)

    def test_session_name_flag_never_touches_prefs(self):
        with tempfile.TemporaryDirectory() as home:
            r = subprocess.run(["python3", str(BIN / "fleet.py"), "--session-name"],
                                env={**os.environ, "ANDERSON_FLEET_DIR": home}, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(r.stdout.strip().startswith("fleet-"))
            self.assertFalse(os.path.exists(os.path.join(home, "prefs.json")))


if __name__ == "__main__":
    unittest.main()
