"""The band mod's persona names match the statusline's, stage for stage, so the two never disagree."""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BAND = (ROOT / "hooks" / "band" / "band.ts").read_text()
STATUSLINE = (ROOT / "bin" / "statusline.sh").read_text()

# agent file -> the pipeline stage it runs at
STAGE = {"planner": "plan", "plan-reviewer": "plan_review", "implementer": "implement",
         "test-fixer": "repair", "reviewer": "diff_review"}


class TestBandPersonas(unittest.TestCase):
    def test_same_names_as_statusline(self):
        band = dict(re.findall(r"^\s+'?([a-z-]+)'?: '([A-Z ]+)',$", BAND, re.M))
        line = dict(re.findall(r'^\s+(\w+)\)\s+who="([A-Z ]+?) ·', STATUSLINE, re.M))
        for agent, stage in STAGE.items():
            with self.subTest(agent=agent):
                self.assertEqual(band.get(agent), line.get(stage))


if __name__ == "__main__":
    unittest.main()
