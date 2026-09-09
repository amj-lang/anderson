"""fleet.py: the synthesized ring, the sound pref, and the usage staleness marker."""
import importlib.util, json, os, pathlib, tempfile, time, unittest, wave

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin"
_spec = importlib.util.spec_from_file_location("fleet_sound", BIN / "fleet.py")
fleet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet)


class TestRing(unittest.TestCase):
    def test_make_ring_wav_is_a_short_valid_mono_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "sub", "ring.wav")        # creates the directory too
            fleet.make_ring_wav(p)
            with wave.open(p) as w:
                self.assertEqual(w.getnchannels(), 1)
                self.assertEqual(w.getsampwidth(), 2)
                dur = w.getnframes() / w.getframerate()
            self.assertTrue(0.7 < dur < 1.2, dur)
            self.assertLess(os.path.getsize(p), 100_000)

    def test_bundled_sounds_are_short_valid_mono_wavs(self):
        names = fleet.sound_names()
        self.assertEqual(names[0], "phone")
        self.assertTrue({"snare", "hitech", "freeze", "blip", "rift", "jump"} <= set(names), names)
        for n in names:
            p = pathlib.Path(fleet.sound_file(n))
            with wave.open(str(p)) as w:
                self.assertEqual(w.getnchannels(), 1, n)
                dur = w.getnframes() / w.getframerate()
            self.assertTrue(0.1 < dur <= 2.5, (n, dur))
            self.assertLess(p.stat().st_size, 120_000, n)

    def test_pick_a_sound_and_fall_back_to_phone(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = fleet.FLEET_DIR, fleet.RING_WAV, fleet.SOUNDS_USER, fleet.RING
            fleet.FLEET_DIR = tmp; fleet.RING_WAV = os.path.join(tmp, "ring.wav")
            fleet.SOUNDS_USER = os.path.join(tmp, "sounds")
            try:
                fleet.RING = "snare"
                self.assertTrue(fleet.ring_path().endswith("snare.wav"))
                fleet.RING = "no-such-sound"
                self.assertTrue(fleet.ring_path().endswith("phone.wav"))
                os.makedirs(fleet.SOUNDS_USER); fleet.make_ring_wav(os.path.join(fleet.SOUNDS_USER, "mine.wav"))
                self.assertIn("mine", fleet.sound_names())
                fleet.RING = "mine"
                self.assertEqual(fleet.ring_path(), os.path.join(fleet.SOUNDS_USER, "mine.wav"))
            finally:
                fleet.FLEET_DIR, fleet.RING_WAV, fleet.SOUNDS_USER, fleet.RING = old

    def test_ring_path_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = fleet.FLEET_DIR, fleet.RING_WAV
            fleet.FLEET_DIR = tmp; fleet.RING_WAV = os.path.join(tmp, "ring.wav")
            try:
                self.assertTrue(fleet.ring_path().endswith("phone.wav"))           # bundled by default
                fleet.make_ring_wav(fleet.RING_WAV)
                self.assertEqual(fleet.ring_path(), fleet.RING_WAV)                 # yours wins
            finally:
                fleet.FLEET_DIR, fleet.RING_WAV = old

    def test_sound_pref_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = fleet.FLEET_DIR, fleet.PREFS_FILE
            fleet.FLEET_DIR = tmp; fleet.PREFS_FILE = os.path.join(tmp, "prefs.json")
            try:
                self.assertFalse(fleet.load_prefs()["sound"])
                fleet.save_prefs(sound=True)
                self.assertTrue(fleet.load_prefs()["sound"])
                self.assertEqual(fleet.load_prefs()["ring"], "phone")
                save = fleet.save_prefs(ring="jump")
                self.assertEqual(fleet.load_prefs()["ring"], "jump")
            finally:
                fleet.FLEET_DIR, fleet.PREFS_FILE = old


class TestUsageStaleness(unittest.TestCase):
    def _with_limits(self, age_s):
        tmp = tempfile.mkdtemp()
        json.dump({"session_id": "u", "ts": time.time() - age_s,
                   "limits": {"five_hour": {"pct": 42, "resets_at": time.time() + 3600}}},
                  open(os.path.join(tmp, "u.status.json"), "w"))
        return tmp

    def _run(self, tmp, fn):
        old = fleet.FLEET_DIR; fleet.FLEET_DIR = tmp
        try:
            return fn()
        finally:
            fleet.FLEET_DIR = old

    def test_fresh_numbers_have_no_marker(self):
        out = self._run(self._with_limits(10), fleet.usage_limits)
        self.assertIn("session 42%", out); self.assertNotIn("as of", out)

    def test_old_numbers_say_how_old(self):
        out = self._run(self._with_limits(15 * 60), fleet.usage_limits)
        self.assertIn("as of 15m ago", out)

    def test_ancient_numbers_are_dropped(self):
        self.assertEqual(self._run(self._with_limits(7 * 3600), fleet.usage_limits), "")

    def test_usage_line_sits_under_the_title_with_bars(self):
        tmp = self._with_limits(10)
        def go():
            lines = fleet.render(fleet.demo_rows(), 140, height=40)
            kinds = [k for k, _ in lines]
            self.assertEqual(kinds[0], "hdr"); self.assertEqual(kinds[1], "usage")
            self.assertIn("session " + fleet.G["bar"] * 4 + fleet.G["trk"] * 6 + " 42%", lines[1][1])
            self.assertEqual(len(lines), 40)
            foot = [ln for k, ln in lines if k in ("foot", "foot_hot")]
            self.assertFalse(any("session" in ln for ln in foot))        # not repeated at the bottom
            for _, ln in lines:
                self.assertEqual(fleet.dw(ln), 140)
        self._run(tmp, go)

    def test_no_limits_means_api_estimate_in_the_footer_only(self):
        tmp = tempfile.mkdtemp()
        def go():
            lines = fleet.render(fleet.demo_rows(), 140, height=30)
            self.assertNotIn("usage", [k for k, _ in lines])
            self.assertIn("api est $", lines[-1][1])
        self._run(tmp, go)

    def test_usage_hot_threshold(self):
        tmp = tempfile.mkdtemp()
        json.dump({"session_id": "h", "ts": time.time(), "limits": {"five_hour": {"pct": 91}}},
                  open(os.path.join(tmp, "h.status.json"), "w"))
        self.assertTrue(self._run(tmp, fleet.usage_hot))


if __name__ == "__main__":
    unittest.main()
