"""stdlib unittest for bin/fleet.py (THE OPERATOR), bin/heartbeat.py, hooks/fleet_event.py.
Alignment is the invariant: every rendered line is exactly the terminal width, at any width,
with any content (CJK, accents, emoji, empty, overlong)."""
import importlib.util, json, os, pathlib, subprocess, tempfile, time, unittest

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin"
HOOKS = pathlib.Path(__file__).resolve().parents[1] / "hooks"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fleet = _load(BIN / "fleet.py", "fleet")


class TestWidth(unittest.TestCase):
    def test_dw_counts_cells_not_codepoints(self):
        self.assertEqual(fleet.dw("abc"), 3)
        self.assertEqual(fleet.dw("日本"), 4)          # wide
        self.assertEqual(fleet.dw("é"), 1)       # combining accent
        self.assertEqual(fleet.dw("🐈"), 2)            # emoji plane
        self.assertEqual(fleet.dw("☎▶✝⟲"), 4)          # the fleet glyphs are 1 cell each

    def test_fit_is_exact(self):
        for s in ["", "x", "日本語のタスク", "a-very-long-repository-name", "déjà vu", "🐈 déjà vu"]:
            for w in (0, 1, 2, 3, 5, 8, 20):
                self.assertEqual(fleet.dw(fleet.fit(s, w)), w, (s, w))
                self.assertEqual(fleet.dw(fleet.fit(s, w, "r")), w, (s, w))

    def test_fit_truncates_with_ellipsis(self):
        self.assertTrue(fleet.fit("abcdefgh", 5).endswith("…"))
        self.assertEqual(fleet.fit("abc", 5), "abc  ")
        self.assertEqual(fleet.fit("abc", 5, "r"), "  abc")


class TestRender(unittest.TestCase):
    def test_every_line_is_terminal_width(self):
        rows = fleet.demo_rows()
        for width in list(range(40, 240, 9)) + [300]:
            for lines in (fleet.render(rows, width, sel=1, frame=3, toast="Wake up, Neo…", burst={"demo-2"}),
                          fleet.render([], width), fleet.render(rows, width, filt="fash")):
                for kind, ln in lines:
                    self.assertEqual(fleet.dw(ln), width, (width, kind, ln))

    def test_layout_sheds_columns_when_narrow(self):
        wide = {k for k, *_ in fleet.layout(200)}
        narrow = {k for k, *_ in fleet.layout(80)}
        self.assertIn("model", wide); self.assertIn("ctx", wide)
        self.assertNotIn("model", narrow); self.assertNotIn("ctx", narrow)
        self.assertIn("ctxp", narrow)                  # compact ctx replaces the bar
        for k in ("repo", "task", "persona", "stage"):
            self.assertIn(k, narrow)

    def test_empty_fleet_has_no_spoon(self):
        text = "\n".join(ln for _, ln in fleet.render([], 100))
        self.assertIn("There is no spoon", text)

    def test_selftest_passes(self):
        self.assertEqual(fleet.selftest(), 0)


class TestTranscript(unittest.TestCase):
    def _write(self, recs):
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        for r in recs:
            f.write(json.dumps(r) + "\n")
        f.close()
        self.addCleanup(os.remove, f.name)
        return f.name

    def test_tool_pending_means_working(self):
        p = self._write([
            {"type": "user", "timestamp": "2026-09-08T10:00:00Z", "message": {"role": "user", "content": "go"}},
            {"type": "assistant", "timestamp": "2026-09-08T10:00:05Z", "message": {
                "model": "claude-sonnet-5", "usage": {"input_tokens": 1000, "cache_read_input_tokens": 50000},
                "content": [{"type": "text", "text": "Running tests."},
                            {"type": "tool_use", "name": "Bash", "input": {"command": "pytest -q\necho done"}}]}},
        ])
        t = fleet.read_transcript(p)
        self.assertEqual(t["state"], "tool")
        self.assertEqual(t["tool"], "Bash")
        self.assertEqual(t["tool_arg"], "pytest -q")
        self.assertEqual(t["ctx_tokens"], 51000)
        self.assertEqual(t["text"], "Running tests.")
        self.assertIsNotNone(t["start"])

    def test_text_only_turn_means_waiting_on_human(self):
        p = self._write([
            {"type": "assistant", "timestamp": "2026-09-08T10:00:05Z", "message": {
                "content": [{"type": "text", "text": "Done. Your call."}]}},
        ])
        self.assertEqual(fleet.read_transcript(p)["state"], "idle")

    def test_tool_result_in_means_thinking(self):
        p = self._write([
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/a/b.py"}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "..."}]}},
        ])
        self.assertEqual(fleet.read_transcript(p)["state"], "think")

    def test_sidechain_tail_means_subagent_running(self):
        p = self._write([
            {"type": "assistant", "isSidechain": False, "message": {"content": [
                {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "anderson:implementer"}}]}},
            {"type": "assistant", "isSidechain": True, "message": {"content": [{"type": "text", "text": "editing"}]}},
        ])
        t = fleet.read_transcript(p)
        self.assertEqual((t["state"], t["tool"], t["tool_arg"]), ("tool", "Agent", "anderson:implementer"))

    def test_missing_file_is_harmless(self):
        self.assertIsNone(fleet.read_transcript("/nope/none.jsonl")["state"])


class TestState(unittest.TestCase):
    def test_anderson_state_reads_latest_and_lenient(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = pathlib.Path(tmp) / "feature-research" / "old"; a.mkdir(parents=True)
            (a / "state.md").write_text("task: old\nstage: plan\n")
            os.utime(a / "state.md", (1, 1))
            b = pathlib.Path(tmp) / "feature-research" / "new"; b.mkdir(parents=True)
            (b / "state.md").write_text("- **task:** new\n- **stage:** diff_review # c\niteration: 1\nmax_iterations: 2\n")
            st = fleet.anderson_state(tmp)
            self.assertEqual((st["task"], st["stage"], st["iteration"], st["max_iterations"]),
                             ("new", "diff_review", "1", "2"))

    def test_enc_cwd_matches_claude_projects_dir(self):
        self.assertEqual(fleet.enc_cwd("/Users/alex_mj/workspace/claude-loop"), "-Users-alex-mj-workspace-claude-loop")


class TestEmitters(unittest.TestCase):
    """heartbeat.py and fleet_event.py write one atomic JSON each; fleet.discover() merges them."""

    def test_heartbeat_then_event_then_discover(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "ANDERSON_FLEET_DIR": tmp, "TMUX_PANE": "%7"}
            sid = "11111111-2222-3333-4444-555555555555"
            hb = {"session_id": sid, "cwd": tmp, "transcript_path": "/none.jsonl",
                  "model": {"id": "claude-fable-5-1", "display_name": "Fable"},
                  "cost": {"total_cost_usd": 1.5, "total_duration_ms": 60000, "total_lines_added": 3, "total_lines_removed": 1},
                  "context_window": {"context_window_size": 200000,
                                     "current_usage": {"input_tokens": 10000, "cache_read_input_tokens": 90000}}}
            r = subprocess.run(["python3", str(BIN / "heartbeat.py")], input=json.dumps(hb), text=True, env=env, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            ev = {"session_id": sid, "hook_event_name": "Notification", "notification_type": "permission_prompt",
                  "cwd": tmp, "transcript_path": "/none.jsonl"}
            r = subprocess.run(["python3", str(HOOKS / "fleet_event.py")], input=json.dumps(ev), text=True, env=env, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "")                      # the hook never steers the session
            st = json.load(open(os.path.join(tmp, f"{sid}.status.json")))
            self.assertEqual((st["cost_usd"], st["ctx_pct"], st["tmux_pane"], st["model"]), (1.5, 50.0, "%7", "Fable"))
            evj = json.load(open(os.path.join(tmp, f"{sid}.event.json")))
            self.assertTrue(evj["waiting"])
            # merge: the emitter's parent (this test runner) is alive, the event says permission_prompt
            old = fleet.FLEET_DIR
            fleet.FLEET_DIR = tmp
            try:
                rows = fleet.discover(include_ps=False)
            finally:
                fleet.FLEET_DIR = old
            self.assertEqual(len(rows), 1)
            r0 = rows[0]
            self.assertEqual((r0["cost"], r0["ctx_pct"], r0["tmux_pane"]), (1.5, 50.0, "%7"))
            self.assertEqual(r0["status"], "ring")
            self.assertIn("permission", r0["now"])

    def test_garbage_input_never_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "ANDERSON_FLEET_DIR": tmp}
            for script in (BIN / "heartbeat.py", HOOKS / "fleet_event.py"):
                for payload in ("", "not json", "{}", '{"session_id": null}'):
                    r = subprocess.run(["python3", str(script)], input=payload, text=True, env=env, capture_output=True)
                    self.assertEqual((r.returncode, r.stdout), (0, ""), (script, payload, r.stderr))
            self.assertEqual(os.listdir(tmp), [])


class TestStatuslineWrapper(unittest.TestCase):
    def test_wrapper_passes_json_through_and_heartbeats(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "ANDERSON_FLEET_DIR": tmp}
            payload = json.dumps({"session_id": "abc", "cwd": tmp, "model": {"display_name": "Opus"}})
            r = subprocess.run(["bash", str(BIN / "fleet-statusline.sh"), "cat"], input=payload, text=True, env=env, capture_output=True)
            self.assertEqual(r.stdout, payload)
            for _ in range(50):                                # heartbeat is backgrounded
                if os.path.exists(os.path.join(tmp, "abc.status.json")):
                    break
                time.sleep(0.05)
            self.assertTrue(os.path.exists(os.path.join(tmp, "abc.status.json")))


class TestPrefsAndWording(unittest.TestCase):
    def test_prefs_roundtrip_and_plain_wording(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_dir, old_prefs, old_plain = fleet.FLEET_DIR, fleet.PREFS_FILE, fleet.PLAIN
            fleet.FLEET_DIR = tmp; fleet.PREFS_FILE = os.path.join(tmp, "prefs.json")
            try:
                p0 = fleet.load_prefs()
                self.assertEqual((p0["theme"], p0["plain"], p0["calm"]), ("matrix", False, False))
                fleet.save_prefs(theme="zion", plain=True)
                p1 = fleet.load_prefs()
                self.assertEqual((p1["theme"], p1["plain"], p1["calm"]), ("zion", True, False))
                fleet.save_prefs(calm=True)                        # partial update keeps the rest
                self.assertEqual(fleet.load_prefs()["theme"], "zion")
                fleet.PLAIN = True
                hdr = fleet.render(fleet.demo_rows(), 120)[0][1]
                self.assertIn("fleet ·", hdr); self.assertIn("waiting", hdr); self.assertNotIn("zion", hdr)
                fleet.PLAIN = False
                hdr = fleet.render(fleet.demo_rows(), 120)[0][1]
                self.assertIn("zion ·", hdr); self.assertIn("jacked in", hdr)
            finally:
                fleet.FLEET_DIR, fleet.PREFS_FILE, fleet.PLAIN = old_dir, old_prefs, old_plain

    def test_every_theme_renders_aligned(self):
        for name in fleet.THEME_ORDER:
            fleet.set_theme(name)
            for kind, ln in fleet.render(fleet.demo_rows(), 100, frame=1):
                self.assertEqual(fleet.dw(ln), 100, (name, kind))
        fleet.set_theme("matrix")

    def test_unknown_theme_falls_back(self):
        self.assertEqual(fleet.set_theme("neo-tokyo")["name"], "matrix")


class TestLauncher(unittest.TestCase):
    def test_install_shim_then_run_once_then_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "FLEET_BIN_DIR": tmp, "ANDERSON_FLEET_DIR": tmp}
            r = subprocess.run(["bash", str(BIN / "fleet"), "install"], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            shim = os.path.join(tmp, "fleet")
            self.assertTrue(os.access(shim, os.X_OK))
            r = subprocess.run(["bash", shim, "--once", "--demo", "--width=90"], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("T H E  O P E R A T O R", r.stdout)
            for ln in r.stdout.rstrip("\n").split("\n"):
                self.assertEqual(fleet.dw(ln), 90)
            r = subprocess.run(["bash", str(BIN / "fleet"), "uninstall"], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(os.path.exists(shim))


class TestJackIn(unittest.TestCase):
    def test_dev_tty_parsing(self):
        self.assertEqual(fleet._dev_tty(" ttys003\n"), "/dev/ttys003")
        for bad in ("??", "-", "", None, "  "):
            self.assertIsNone(fleet._dev_tty(bad))

    def test_focus_scripts_target_the_tty(self):
        for app in ("iTerm2", "Terminal"):
            sc = fleet._focus_script(app, "/dev/ttys042")
            self.assertIn('"/dev/ttys042"', sc)
            self.assertNotIn("{tty}", sc)
            self.assertTrue(sc.rstrip().endswith('return "miss"'))
        self.assertIn("sessions of t", fleet._focus_script("iTerm2", "/dev/x"))
        self.assertIn("selected tab of w", fleet._focus_script("Terminal", "/dev/x"))

    def test_owner_app_never_raises(self):
        self.assertIn(type(fleet._owner_app(os.getpid())), (type(None), tuple))
        self.assertIsNone(fleet._owner_app(1))
        self.assertIsNone(fleet._owner_app(None))

    def test_jack_in_without_pane_or_pid_explains(self):
        msg = fleet.jack_in({"tmux_pane": None, "pid": None})
        self.assertIn("tmux", msg)


class TestUsageLimits(unittest.TestCase):
    def test_heartbeat_stores_limits_and_footer_shows_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "ANDERSON_FLEET_DIR": tmp}
            hb = {"session_id": "lim", "cwd": tmp, "rate_limits": {
                "five_hour": {"used_percentage": 20.4, "resets_at": time.time() + 4 * 3600 + 33 * 60},
                "seven_day": {"used_percentage": 37.9, "resets_at": time.time() + 3 * 86400}}}
            r = subprocess.run(["python3", str(BIN / "heartbeat.py")], input=json.dumps(hb), text=True, env=env, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            st = json.load(open(os.path.join(tmp, "lim.status.json")))
            self.assertEqual(st["limits"]["five_hour"]["pct"], 20.4)
            old = fleet.FLEET_DIR; fleet.FLEET_DIR = tmp
            try:
                lim = fleet.usage_limits()
                self.assertIn("session 20%", lim); self.assertIn("week 37%", lim); self.assertRegex(lim, r"4h3[23] left")
                lines = fleet.render([], 140)
                head = lines[1][1]; foot = lines[-1][1]
                self.assertEqual(lines[1][0], "usage")
                self.assertIn("session ", head); self.assertIn(" 20%", head)              # up top, with a bar
                self.assertNotIn("api est", foot); self.assertNotIn("session", foot)      # subscription: no $, not repeated
                self.assertNotIn("cost", {k for k, *_ in fleet.layout(200)})            # api$ column hidden
                fleet.SHOW_COST = True
                try:
                    self.assertIn("api est", fleet.render([], 140)[-1][1])
                    self.assertIn("cost", {k for k, *_ in fleet.layout(200)})
                finally:
                    fleet.SHOW_COST = False
                for kind, ln in fleet.render(fleet.demo_rows(), 140):
                    self.assertEqual(fleet.dw(ln), 140)
            finally:
                fleet.FLEET_DIR = old

    def test_no_limits_no_footer_noise(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = fleet.FLEET_DIR; fleet.FLEET_DIR = tmp
            try:
                self.assertEqual(fleet.usage_limits(), "")
                foot = fleet.render([], 120)[-1][1]
                self.assertNotIn("session", foot); self.assertIn("api est", foot)         # API-key user: $ shown
                self.assertIn("cost", {k for k, *_ in fleet.layout(200)})
            finally:
                fleet.FLEET_DIR = old


class TestZoom(unittest.TestCase):
    def test_zoom_pref_roundtrip_and_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = fleet.FLEET_DIR, fleet.PREFS_FILE
            fleet.FLEET_DIR = tmp; fleet.PREFS_FILE = os.path.join(tmp, "prefs.json")
            try:
                self.assertIsNone(fleet.load_prefs()["zoom"])
                fleet.save_prefs(zoom=16); self.assertEqual(fleet.load_prefs()["zoom"], 16)
                fleet.save_prefs(zoom=None); self.assertIsNone(fleet.load_prefs()["zoom"])   # None clears
                fleet.save_prefs(zoom=999); self.assertIsNone(fleet.load_prefs()["zoom"])    # out of range ignored
            finally:
                fleet.FLEET_DIR, fleet.PREFS_FILE = old

    def test_font_control_only_in_terminal_app(self):
        self.assertIsNone(fleet._terminal_font(None))
        old = os.environ.get("TERM_PROGRAM"); os.environ["TERM_PROGRAM"] = "iTerm.app"
        try:
            self.assertIsNone(fleet._terminal_font("/dev/ttys000", 14))     # never calls osascript elsewhere
        finally:
            if old is None: os.environ.pop("TERM_PROGRAM", None)
            else: os.environ["TERM_PROGRAM"] = old


class TestPidResolution(unittest.TestCase):
    def test_orphaned_emitter_reports_no_pid_not_pid_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "ANDERSON_FLEET_DIR": tmp, "FLEET_PID": "1"}
            r = subprocess.run(["python3", str(BIN / "heartbeat.py")], input=json.dumps({"session_id": "orph", "cwd": tmp}),
                               text=True, env=env, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIsNone(json.load(open(os.path.join(tmp, "orph.status.json")))["pid"])

    def test_fleet_treats_pid_1_as_unknown_not_alive(self):
        with tempfile.TemporaryDirectory() as tmp:
            json.dump({"session_id": "s1", "cwd": tmp, "pid": 1, "ts": time.time(), "cost_usd": 0.1},
                      open(os.path.join(tmp, "s1.status.json"), "w"))
            old = fleet.FLEET_DIR; fleet.FLEET_DIR = tmp
            try:
                rows = fleet.discover(include_ps=False)
            finally:
                fleet.FLEET_DIR = old
            self.assertEqual(len(rows), 1)
            self.assertIsNone(rows[0]["pid"])
            self.assertNotEqual(rows[0]["status"], "sentinel")

    def test_layout_caps_elastic_columns(self):
        widths = {k: w for k, _, w, _ in fleet.layout(300)}
        self.assertLessEqual(widths["repo"], 28); self.assertLessEqual(widths["task"], 56)
        for kind, ln in fleet.render(fleet.demo_rows(), 300):
            self.assertEqual(fleet.dw(ln), 300)


class TestNoProcess(unittest.TestCase):
    def test_unknown_pid_with_no_matching_process_is_sentinel(self):
        with tempfile.TemporaryDirectory() as tmp:
            json.dump({"session_id": "gone", "cwd": tmp, "pid": None, "ts": time.time()},
                      open(os.path.join(tmp, "gone.status.json"), "w"))
            old = fleet.FLEET_DIR; fleet.FLEET_DIR = tmp
            try:
                rows = fleet.discover(include_ps=True)      # ps sees processes, none in this cwd
            finally:
                fleet.FLEET_DIR = old
            mine = [r for r in rows if r["sid"] == "gone"]
            self.assertEqual(len(mine), 1)
            if fleet._ps():                                 # only meaningful where ps works
                self.assertEqual(mine[0]["status"], "sentinel")


class TestNoDuplicateRows(unittest.TestCase):
    """One process = one row: headless `claude -p` children and old session ids never duplicate a session."""
    def _discover(self, tmp, ps):
        old = (fleet.FLEET_DIR, fleet._ps, fleet._cwd_of, fleet.alive, fleet._tmux_panes)
        fleet.FLEET_DIR = tmp; fleet._ps = lambda: ps; fleet._cwd_of = lambda pid: tmp
        fleet.alive = lambda pid: bool(pid); fleet._tmux_panes = lambda: {}
        try:
            return fleet.discover(include_ps=True)
        finally:
            fleet.FLEET_DIR, fleet._ps, fleet._cwd_of, fleet.alive, fleet._tmux_panes = old

    def test_headless_child_claude_is_folded_into_its_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            json.dump({"session_id": "main", "cwd": tmp, "pid": 100, "ts": time.time()},
                      open(os.path.join(tmp, "main.status.json"), "w"))
            ps = [(100, 1, "claude"), (200, 100, "bash -c review"), (300, 200, "claude -p Review this change"),
                  (400, 1, "claude")]                       # 400: a real second session in the same repo
            rows = self._discover(tmp, ps)
            self.assertEqual(sorted(r["pid"] for r in rows), [100, 400])

    def test_hook_sourced_child_sessions_are_folded_too(self):
        """Claude Code's bg daemon (claude daemon -> bg-spare / bg-pty-host) fires hooks under its own session ids."""
        with tempfile.TemporaryDirectory() as tmp:
            now = time.time()
            json.dump({"session_id": "main", "cwd": tmp, "pid": 100, "ts": now}, open(os.path.join(tmp, "main.status.json"), "w"))
            json.dump({"session_id": "spare", "cwd": tmp, "pid": 300, "ts": now, "event": "SessionStart"},
                      open(os.path.join(tmp, "spare.event.json"), "w"))
            json.dump({"session_id": "pty", "cwd": tmp, "pid": 400, "ts": now, "event": "PostToolUse"},
                      open(os.path.join(tmp, "pty.event.json"), "w"))
            ps = [(100, 1, "claude"), (200, 100, "/Users/x/.local/bin/claude daemon run --origin transient"),
                  (300, 200, "claude bg-spare --bg-spare /tmp/cc-daemon/spare/a"), (400, 200, "/x/ClaudeCode.app/Contents/MacOS/claude bg-pty-host")]
            rows = self._discover(tmp, ps)
            self.assertEqual([r["sid"] for r in rows], ["main"])

    def test_same_pid_keeps_only_the_freshest_session_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = time.time()
            json.dump({"session_id": "before-clear", "cwd": tmp, "pid": 100, "ts": now - 3600},
                      open(os.path.join(tmp, "before-clear.status.json"), "w"))
            json.dump({"session_id": "after-clear", "cwd": tmp, "pid": 100, "ts": now},
                      open(os.path.join(tmp, "after-clear.status.json"), "w"))
            rows = self._discover(tmp, [(100, 1, "claude")])
            self.assertEqual([r["sid"] for r in rows], ["after-clear"])


class TestInstallExtras(unittest.TestCase):
    def test_install_reports_extras_and_rejects_unknown_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "FLEET_BIN_DIR": tmp, "HOME": tmp}
            r = subprocess.run(["bash", str(BIN / "fleet"), "install"], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("extras:", r.stdout); self.assertIn("glow", r.stdout); self.assertIn("tmux", r.stdout)
            r = subprocess.run(["bash", str(BIN / "fleet"), "install", "--bogus"], env=env, capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertIn("unknown install flag", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
