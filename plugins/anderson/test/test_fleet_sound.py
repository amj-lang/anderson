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

    def test_bundled_matrix_ring_is_valid_and_short(self):
        p = BIN.parent / "assets" / "ring-matrix.wav"
        self.assertTrue(p.is_file())
        with wave.open(str(p)) as w:
            dur = w.getnframes() / w.getframerate()
            self.assertEqual(w.getnchannels(), 1)
        self.assertTrue(1.5 < dur < 3.0, dur)
        self.assertLess(p.stat().st_size, 120_000)

    def test_ring_path_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = fleet.FLEET_DIR, fleet.RING_WAV
            fleet.FLEET_DIR = tmp; fleet.RING_WAV = os.path.join(tmp, "ring.wav")
            try:
                self.assertTrue(fleet.ring_path().endswith("ring-matrix.wav"))     # bundled by default
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

    def test_usage_hot_threshold(self):
        tmp = tempfile.mkdtemp()
        json.dump({"session_id": "h", "ts": time.time(), "limits": {"five_hour": {"pct": 91}}},
                  open(os.path.join(tmp, "h.status.json"), "w"))
        self.assertTrue(self._run(tmp, fleet.usage_hot))


if __name__ == "__main__":
    unittest.main()
