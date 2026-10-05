"""fleet.py UX batch: session titles, transcript branch, hot-ctx cell span, row numbers, resume command."""
from unittest import mock
import importlib.util, json, os, pathlib, subprocess, tempfile, unittest

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin"
_spec = importlib.util.spec_from_file_location("fleet_ux", BIN / "fleet.py")
fleet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet)


class TestUxBatch(unittest.TestCase):
    def _write(self, recs):
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        for r in recs:
            f.write(json.dumps(r) + "\n")
        f.close()
        self.addCleanup(os.remove, f.name)
        return f.name

    def test_title_is_first_real_prompt_and_branch_from_transcript(self):
        wrapper = "<" + "command-name>/x<" + "/command-name>"      # slash-command wrapper, skipped
        p = self._write([
            {"type": "user", "timestamp": "2026-09-08T10:00:00Z", "message": {"role": "user", "content": wrapper}},
            {"type": "user", "timestamp": "2026-09-08T10:00:01Z", "message": {"role": "user", "content": "fix the lightbox flicker\nsecond line"}},
            {"type": "assistant", "timestamp": "2026-09-08T10:00:05Z", "gitBranch": "feat/lightbox",
             "message": {"content": [{"type": "text", "text": "On it."}]}},
        ])
        t = fleet.read_transcript(p)
        self.assertEqual(t["title"], "fix the lightbox flicker")
        self.assertEqual(t["branch"], "feat/lightbox")

    def test_summary_record_wins_as_title(self):
        p = self._write([{"type": "summary", "summary": "Lightbox flicker fix"},
                         {"type": "user", "message": {"content": "hello"}}])
        self.assertEqual(fleet.read_transcript(p)["title"], "Lightbox flicker fix")

    def test_ctx_span_and_cell_index_are_cell_accurate(self):
        span = fleet.ctx_span(150)
        self.assertIsNotNone(span)
        lines = fleet.render(fleet.demo_rows(), 150)
        top = [k for k, _ in lines].index("colhdr") + 1
        line = lines[top][1]
        i0 = fleet.cell_index(line, span[0]); i1 = fleet.cell_index(line, span[0] + span[1])
        self.assertIn("%", line[i0:i1])                       # the slice is the ctx cell
        self.assertEqual(fleet.cell_index("日本x", 4), 2)        # two wide chars = 4 cells
        self.assertIsNone(fleet.ctx_span(60))                 # hidden when narrow

    def test_rows_are_numbered(self):
        lines = fleet.render(fleet.demo_rows(), 150)
        top = [k for k, _ in lines].index("colhdr") + 1
        self.assertTrue(lines[top][1].startswith("1"))
        self.assertTrue(lines[top + 1][1].startswith("2"))

    def test_resume_cmd(self):
        self.assertIsNone(fleet.resume_cmd({"sid": "pid:12", "cwd": "/x"}))
        self.assertIsNone(fleet.resume_cmd({"sid": "demo-1", "cwd": "/x"}))
        cmd = fleet.resume_cmd({"sid": "8596c744-4f19-48ac-ac12-7f4445578e3d", "cwd": "/Users/a b/repo"})
        self.assertEqual(cmd, "claude --resume 8596c744-4f19-48ac-ac12-7f4445578e3d")   # revive() passes the cwd

    def test_hot_rows_ignore_sentinels_and_unknown_ctx(self):
        rows = fleet.demo_rows()
        rows[0]["ctx_pct"] = 85; rows[1]["ctx_pct"] = None
        rows[3]["ctx_pct"] = 99                              # demo row 3 is the sentinel
        self.assertEqual(fleet.hot_rows(rows), {rows[0]["sid"]})

    def test_title_kept_on_sentinel_rows(self):
        row = dict(fleet.demo_rows()[3], task="", title="old work")
        self.assertEqual(fleet.cell(row, "task", 0), '"old work"')


class TestPinnedFooter(unittest.TestCase):
    def test_footer_sits_on_the_last_lines_and_keys_never_truncate(self):
        for W, H in ((150, 40), (80, 24), (60, 20)):
            lines = fleet.render(fleet.demo_rows(), W, sel=1, height=H)
            self.assertEqual(len(lines), H, (W, H))
            kinds = [k for k, _ in lines]
            self.assertEqual(kinds[-1] in ("foot", "foot_hot"), True)
            foot_txt = " ".join(ln for k, ln in lines if k == "foot")
            for key in ("N new agent", "m sound", "q quit", "? manual"):
                self.assertIn(key, foot_txt, (W, H, key))
            for _, ln in lines:
                self.assertEqual(fleet.dw(ln), W)

    def test_no_height_means_no_filler(self):
        lines = fleet.render(fleet.demo_rows(), 120)
        self.assertLess(len(lines), 30)
        self.assertEqual(lines[-1][0], "foot")


class TestSubagents(unittest.TestCase):
    def test_counts_and_last_meta(self):
        import time
        with tempfile.TemporaryDirectory() as tmp:
            tp = os.path.join(tmp, "abc.jsonl"); open(tp, "w").write("")
            self.assertEqual(fleet.subagents(tp), (0, 0, ""))
            d = os.path.join(tmp, "abc", "subagents"); os.makedirs(d)
            for i, name in enumerate(("agent-a1", "agent-b2", "agent-c3")):
                open(os.path.join(d, name + ".jsonl"), "w").write("{}")
                os.utime(os.path.join(d, name + ".jsonl"), (time.time() - 600 + i, time.time() - 600 + i))
            json.dump({"agentType": "anderson:reviewer", "description": "Diff-review AR-1", "model": "fable"},
                      open(os.path.join(d, "agent-c3.meta.json"), "w"))
            self.assertEqual(fleet.subagents(tp), (3, 0, 'anderson:reviewer "Diff-review AR-1" (fable)'))
            os.utime(os.path.join(d, "agent-c3.jsonl"), None)                 # touched now: running
            self.assertEqual(fleet.subagents(tp)[1], 1)

    def test_card_shows_agents_line_only_when_any(self):
        r = {**fleet.demo_rows()[1], "agents": (4, 1, "anderson:reviewer (fable)")}
        card = " ".join(ln for _, ln in fleet.detail_card(r, 140, "", 0, airy=True))
        self.assertIn("agents", card); self.assertIn("4 sent · 1 running · last anderson:reviewer (fable)", card)
        r["agents"] = (0, 0, "")
        self.assertNotIn("agents", " ".join(ln for _, ln in fleet.detail_card(r, 140, "", 0, airy=True)))


class TestDismiss(unittest.TestCase):
    def test_hidden_rows_stay_hidden_and_clean_removes_state_files(self):
        import time
        with tempfile.TemporaryDirectory() as tmp:
            old = fleet.FLEET_DIR; fleet.FLEET_DIR = tmp
            try:
                for sid, pid in (("live", os.getpid()), ("gone", None)):
                    json.dump({"session_id": sid, "cwd": tmp, "pid": pid, "ts": time.time()},
                              open(os.path.join(tmp, sid + ".status.json"), "w"))
                self.assertEqual(sorted(r["sid"] for r in fleet.discover(include_ps=False)), ["gone", "live"])
                fleet.dismiss("live")                      # hide, keep files (a running session keeps writing them)
                fleet.dismiss("gone", clean=True)          # dead row: files go too
                self.assertTrue(os.path.exists(os.path.join(tmp, "live.status.json")))
                self.assertFalse(os.path.exists(os.path.join(tmp, "gone.status.json")))
                self.assertEqual(fleet.discover(include_ps=False), [])
            finally:
                fleet.FLEET_DIR = old

    def test_footer_uses_plain_words(self):
        foot = " ".join(ln for k, ln in fleet.footer(fleet.demo_rows(), 160) if k == "foot")
        self.assertIn("r kill", foot); self.assertIn("b hide", foot); self.assertNotIn("pill", foot)


class TestShowHidden(unittest.TestCase):
    def test_hidden_rows_listed_flagged_and_unhidden(self):
        import time
        with tempfile.TemporaryDirectory() as tmp:
            old = fleet.FLEET_DIR; fleet.FLEET_DIR = tmp
            try:
                json.dump({"session_id": "x", "cwd": tmp, "pid": None, "ts": time.time()},
                          open(os.path.join(tmp, "x.status.json"), "w"))
                fleet.dismiss("x")
                self.assertEqual(fleet.discover(include_ps=False), [])
                rows = fleet.discover(include_ps=False, hidden=True)
                self.assertEqual([r["sid"] for r in rows], ["x"]); self.assertTrue(rows[0]["hidden"])
                self.assertIn(fleet.G["hid"], fleet.cell(rows[0], "flag", 0))
                lines = fleet.render(rows, 120)
                self.assertIn("1 hidden", lines[0][1])
                self.assertTrue(any(k == "hidden_sel" for k, _ in lines))
                fleet.unhide("x")
                self.assertEqual([r["sid"] for r in fleet.discover(include_ps=False)], ["x"])
                self.assertFalse(fleet.discover(include_ps=False)[0]["hidden"])
            finally:
                fleet.FLEET_DIR = old

    def test_footer_keeps_width_and_lists_only_the_kept_keys(self):
        for W in (200, 120, 80, 50):
            for _, ln in fleet.footer(fleet.demo_rows(), W):
                self.assertEqual(fleet.dw(ln), W)
        wide = " ".join(ln for k, ln in fleet.footer(fleet.demo_rows(), 200) if k == "foot")
        for key in ("r kill", "b hide", "m sound", "h hidden", "space fold", "w next ring"):
            self.assertIn(key, wide)
        for gone in ("R rebase", "J/K", "D pop", "O in IDE", "a agent", "c resume", "zoom", "t theme", "$ cost"):
            self.assertNotIn(gone, wide)


class TestLookingAt(unittest.TestCase):
    """Alerts are skipped when the session's own terminal is what the human is looking at."""
    def setUp(self):
        self.old = {k: getattr(fleet, k) for k in ("_front_app", "_selected_tty", "_tty_of", "_owner_app", "ghostty_tid", "_jxa")}
        self.row = {"pid": 4242, "tmux_pane": None}
        fleet._tty_of = lambda pid: "/dev/ttys005"
        fleet._owner_app = lambda pid: ("WebStorm", "/Applications/WebStorm.app", 9)

    def tearDown(self):
        for k, v in self.old.items():
            setattr(fleet, k, v)

    def test_terminal_tab_match(self):
        import sys
        if sys.platform != "darwin":
            self.skipTest("macOS only")
        fleet._owner_app = lambda pid: ("Terminal", "/System/Applications/Utilities/Terminal.app", 9)
        fleet._front_app = lambda: ("com.apple.Terminal", "Terminal")
        fleet._selected_tty = lambda b: "/dev/ttys005"
        self.assertTrue(fleet.looking_at(self.row))
        fleet._selected_tty = lambda b: "/dev/ttys011"
        self.assertFalse(fleet.looking_at(self.row))

    def test_ghostty_in_front_is_not_enough_its_focused_tab_must_be_the_session(self):
        """The bug: any Ghostty window in front (fleet's own tab, say) counted as watching every
        Ghostty session, so their rings were swallowed."""
        import sys
        if sys.platform != "darwin":
            self.skipTest("macOS only")
        fleet._owner_app = lambda pid: ("Ghostty", "/Applications/Ghostty.app", 9)
        fleet._front_app = lambda: ("com.mitchellh.ghostty", "Ghostty")
        fleet.ghostty_tid = lambda r, app_pid: ("T-SESSION", None)
        fleet._jxa = lambda script: mock.Mock(stdout="T-FLEET\n")
        self.assertFalse(fleet.looking_at(self.row))
        fleet._jxa = lambda script: mock.Mock(stdout="T-SESSION\n")
        self.assertTrue(fleet.looking_at(self.row))
        fleet._front_app = lambda: ("com.google.Chrome", "Google Chrome")
        self.assertFalse(fleet.looking_at(self.row))

    def test_ide_frontmost_counts_as_watching(self):
        import sys
        if sys.platform != "darwin":
            self.skipTest("macOS only")
        fleet._front_app = lambda: ("com.jetbrains.WebStorm", "WebStorm")
        self.assertTrue(fleet.looking_at(self.row))
        fleet._front_app = lambda: ("com.google.Chrome", "Google Chrome")
        self.assertFalse(fleet.looking_at(self.row))

    def test_unknown_front_or_no_pid_is_false(self):
        fleet._front_app = lambda: ("", "")
        self.assertFalse(fleet.looking_at(self.row))
        self.assertFalse(fleet.looking_at({"pid": None, "tmux_pane": None}))

    def test_dev_tty_normalizes_both_forms(self):
        self.assertEqual(fleet._dev_tty("ttys005 \n"), "/dev/ttys005")
        self.assertEqual(fleet._dev_tty("/dev/ttys005\n"), "/dev/ttys005")
        self.assertIsNone(fleet._dev_tty("??"))


class TestBreathingRoom(unittest.TestCase):
    def test_tall_terminal_gets_spacers_short_one_does_not(self):
        rows = fleet.demo_rows()
        tall = [k for k, _ in fleet.render(rows, 140, sel=1, height=45)]
        i = tall.index("colhdr")
        self.assertEqual(tall[i - 1], "empty"); self.assertEqual(tall[i - 2], "rule"); self.assertEqual(tall[i - 3], "empty")
        self.assertEqual(tall[i + len(rows) + 1], "empty")                     # gap between the list and its rule
        self.assertEqual(tall[i + len(rows) + 2], "rule"); self.assertEqual(tall[i + len(rows) + 3], "empty")   # and after it
        self.assertEqual(len(tall), 45)
        short = [k for k, _ in fleet.render(rows, 140, sel=1, height=22)]
        j = short.index("colhdr")
        self.assertEqual(short[j - 1], "rule"); self.assertNotIn("empty", short[:j])
        self.assertEqual(len(short), 22)


class TestIdleGoesWhite(unittest.TestCase):
    def test_old_ring_is_idle_kind_fresh_ring_still_rings(self):
        rows = fleet.demo_rows()
        fresh, old = rows[0], rows[2]
        self.assertEqual(fresh["status"], "ring"); self.assertEqual(old["status"], "ring")
        fresh["idle"], old["idle"] = False, True
        kinds = [k for k, _ in fleet.render(rows, 150, sel=0)]
        top = kinds.index("colhdr") + 1
        self.assertEqual(kinds[top], "ring_sel"); self.assertEqual(kinds[top + 2], "idle")

    def test_enrich_marks_idle_after_five_minutes(self):
        import time
        with tempfile.TemporaryDirectory() as tmp:
            now = time.time()
            def row(age):
                ev = {"session_id": "e", "waiting": True, "ts": now - age, "event": "Stop"}
                return fleet.enrich({"sid": "e", "src": {"event"}, "cwd": tmp, "pid": os.getpid(), "ev": ev}, now)
            self.assertFalse(row(60)["idle"]); self.assertEqual(row(60)["status"], "ring")
            self.assertTrue(row(fleet.IDLE_S + 1)["idle"]); self.assertEqual(row(fleet.IDLE_S + 1)["status"], "ring")


class TestRings(unittest.TestCase):
    """When a row rings. Hooks are the truth; the transcript only fills what no hook reports."""
    NOW = 1_000_000.0

    def status(self, ev, tr, dead=False):
        return fleet.row_status(ev, {"state": None, "ts": None, **tr}, dead, self.NOW)

    def test_mid_turn_text_never_rings_when_hooks_exist(self):
        """The bug: a "Now let me check X" text line is newer than the last PostToolUse and reads
        like a finished turn, so every turn rang several times."""
        ev = {"event": "PostToolUse", "waiting": False, "ts": self.NOW - 3}
        self.assertEqual(self.status(ev, {"state": "idle", "ts": self.NOW - 1})[0], "work")

    def test_stop_and_permission_ring(self):
        st, txt, since = self.status({"event": "Stop", "waiting": True, "ts": self.NOW - 60}, {})
        self.assertEqual((st, since), ("ring", self.NOW - 60))
        perm = {"event": "Notification", "waiting": True, "ts": self.NOW, "notification": "permission_prompt"}
        self.assertIn("permission Bash", self.status(perm, {"state": "tool", "tool": "Bash", "ts": self.NOW})[1])

    def test_ring_keeps_its_start_across_the_idle_notification(self):
        ev = {"event": "Notification", "waiting": True, "ts": self.NOW, "since": self.NOW - 90}
        self.assertEqual(self.status(ev, {})[2], self.NOW - 90)

    def test_a_question_tool_rings(self):
        ev = {"event": "PreToolUse", "waiting": False, "ts": self.NOW}
        for tool in ("AskUserQuestion", "ExitPlanMode"):
            self.assertEqual(self.status(ev, {"state": "tool", "tool": tool, "ts": self.NOW})[0], "ring")
        self.assertEqual(self.status(ev, {"state": "tool", "tool": "Bash", "ts": self.NOW})[0], "work")

    def test_interrupted_turn_rings_only_after_long_silence(self):
        ev = {"event": "PostToolUse", "waiting": False, "ts": self.NOW - fleet.STUCK_S - 99}
        self.assertEqual(self.status(ev, {"state": "think", "ts": self.NOW - 60})[0], "work")
        self.assertEqual(self.status(ev, {"state": "think", "ts": self.NOW - fleet.STUCK_S - 1})[1].split()[1], "idle")
        self.assertEqual(self.status(ev, {"state": "tool", "tool": "Bash", "ts": self.NOW - fleet.STUCK_S - 1})[0], "work")

    def test_fresh_session_is_not_waiting_on_you(self):
        ev = {"event": "SessionStart", "waiting": False, "ts": self.NOW}
        self.assertEqual(self.status(ev, {"state": "idle", "ts": self.NOW - 86400})[0], "work")

    def test_hookless_session_guesses_from_the_transcript_after_a_pause(self):
        self.assertEqual(self.status({}, {"state": "idle", "ts": self.NOW - 2})[0], "work")
        self.assertEqual(self.status({}, {"state": "idle", "ts": self.NOW - fleet.GUESS_S - 1})[0], "ring")

    def test_a_stop_the_session_moved_past_is_stale(self):
        """A blocked Stop on a session whose hooks predate PreToolUse: the transcript shows it working."""
        ev = {"event": "Stop", "waiting": True, "ts": self.NOW - 100}
        self.assertEqual(self.status(ev, {"state": "tool", "tool": "Agent", "ts": self.NOW - 5})[0], "work")
        perm = {"event": "Notification", "waiting": True, "ts": self.NOW, "notification": "permission_prompt"}
        self.assertEqual(self.status(perm, {"state": "tool", "tool": "Bash", "ts": self.NOW - 2})[0], "ring")

    def test_dead_beats_everything(self):
        self.assertEqual(self.status({"waiting": True, "ts": self.NOW}, {}, dead=True)[0], "sentinel")

    def test_due_rings_settle_then_alert_once(self):
        row = lambda since: {"sid": "a", "status": "ring", "since": since}
        fresh, rung = fleet.due_rings([row(self.NOW - 1)], set(), self.NOW)
        self.assertEqual((fresh, rung), ([], set()))                       # too new: a blocked Stop looks like this
        fresh, rung = fleet.due_rings([row(self.NOW - fleet.RING_SETTLE_S)], rung, self.NOW)
        self.assertEqual([r["sid"] for r in fresh], ["a"])
        fresh, rung = fleet.due_rings([row(self.NOW - 60)], rung, self.NOW)
        self.assertEqual(fresh, [])                                         # once
        fresh, rung = fleet.due_rings([{"sid": "a", "status": "work"}], rung, self.NOW)
        self.assertEqual(rung, set())                                       # stopped ringing: re-armed
        self.assertEqual(len(fleet.due_rings([{"sid": "n", "status": "ring", "since": None}], set(), self.NOW)[0]), 1)
        hidden = {"sid": "h", "status": "ring", "since": 0, "hidden": True}
        self.assertEqual(fleet.due_rings([hidden], set(), self.NOW)[0], [])


class TestEventHook(unittest.TestCase):
    def fire(self, tmp, event, **kw):
        env = {**os.environ, "ANDERSON_FLEET_DIR": tmp}
        payload = {"session_id": "s", "hook_event_name": event, "cwd": tmp, **kw}
        r = subprocess.run(["python3", str(BIN.parent / "hooks" / "fleet_event.py")], input=json.dumps(payload),
                           text=True, env=env, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.load(open(os.path.join(tmp, "s.event.json")))

    def test_pre_tool_use_clears_a_blocked_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(self.fire(tmp, "Stop")["waiting"])
            ev = self.fire(tmp, "PreToolUse", tool_name="Agent")
            self.assertEqual((ev["waiting"], ev["tool"]), (False, "Agent"))

    def test_wait_start_survives_the_idle_notification(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = self.fire(tmp, "Stop")["since"]
            self.assertEqual(self.fire(tmp, "Notification", notification_type="idle_prompt")["since"], first)
            self.fire(tmp, "UserPromptSubmit", prompt="go")
            self.assertGreater(self.fire(tmp, "Stop")["since"], first)       # a new wait starts fresh

    def test_hooks_json_wires_pre_tool_use(self):
        hooks = json.load(open(BIN.parent / "hooks" / "hooks.json"))["hooks"]
        self.assertIn("fleet_event.py", json.dumps(hooks["PreToolUse"]))


if __name__ == "__main__":
    unittest.main()
