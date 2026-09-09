"""fleet.py UX batch: session titles, transcript branch, hot-ctx cell span, row numbers, resume command."""
import importlib.util, json, os, pathlib, tempfile, unittest

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
        line = fleet.render(fleet.demo_rows(), 150)[3][1]
        i0 = fleet.cell_index(line, span[0]); i1 = fleet.cell_index(line, span[0] + span[1])
        self.assertIn("%", line[i0:i1])                       # the slice is the ctx cell
        self.assertEqual(fleet.cell_index("日本x", 4), 2)        # two wide chars = 4 cells
        self.assertIsNone(fleet.ctx_span(60))                 # hidden when narrow

    def test_rows_are_numbered(self):
        lines = fleet.render(fleet.demo_rows(), 150)
        self.assertTrue(lines[3][1].startswith("1"))
        self.assertTrue(lines[4][1].startswith("2"))

    def test_resume_cmd(self):
        self.assertIsNone(fleet.resume_cmd({"sid": "pid:12", "cwd": "/x"}))
        self.assertIsNone(fleet.resume_cmd({"sid": "demo-1", "cwd": "/x"}))
        cmd = fleet.resume_cmd({"sid": "8596c744-4f19-48ac-ac12-7f4445578e3d", "cwd": "/Users/a b/repo"})
        self.assertEqual(cmd, "cd '/Users/a b/repo' && claude --resume 8596c744-4f19-48ac-ac12-7f4445578e3d")

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
            for key in ("s ring", "m sound", "q quit", "? manual"):
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


if __name__ == "__main__":
    unittest.main()
