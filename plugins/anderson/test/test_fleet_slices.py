"""fleet: a split task's row carries its slice tag, and the card names parent, contracts, next slice."""
import importlib.util, os, pathlib, sys, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fleet_fixtures import demo_rows

BIN = pathlib.Path(__file__).resolve().parents[1] / "bin"
_spec = importlib.util.spec_from_file_location("fleet_slices", BIN / "fleet.py")
fleet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet)

SLICES = """# ar-2587-pause slices
parent: https://linear.app/acme/issue/AR-2587/pause
| # | Slice | Criteria | Depends on | Issue | Branch | Status |
|---|-------|----------|------------|-------|--------|--------|
| 1 | pause stops charge | c1 | — | AR-2588 | me/ar-2588-pause | shipped (pr 1) |
| 2 | resume date | c2 | 1 | AR-2589 | me/ar-2589-resume | doing |
| 3 | packed bag | c3 | 1, 2 | AR-2590 | me/ar-2590-packed-bag | todo |
**Contracts:**
- paused_until: date|null — null = not paused
- skipCharge(sub): bool — true while paused ✎ slice 1
## Settled decisions
- bill stops? → end of month
"""


class TestFleetSlices(unittest.TestCase):
    def row(self, **k):
        return {**demo_rows(fleet)[1], **k}

    def test_task_cell_tag_only_when_sliced(self):
        self.assertEqual(fleet.cell(self.row(slice="2/3"), "task", 0), "remove-db-triggers  ✂ 2/3")
        self.assertEqual(fleet.cell(self.row(), "task", 0), "remove-db-triggers")

    def test_slice_line_reads_parent_contracts_and_next(self):
        with tempfile.NamedTemporaryFile("w", suffix=".slices.md", delete=False) as f:
            f.write(SLICES)
        self.addCleanup(os.remove, f.name)
        line = fleet.slice_line(self.row(slice="2/3", slices=f.name))
        self.assertEqual(line, "2/3 of AR-2587 · contracts paused_until ✓ skipCharge(sub) ✎"
                               " · next ar-2590-packed-bag (waits on 2)")

    def test_slice_line_without_file_is_just_k_of_n(self):
        self.assertEqual(fleet.slice_line(self.row(slice="2/3", slices="/nope.slices.md")), "2/3")

    def test_card_shows_slice_line(self):
        lines = fleet.detail_card(self.row(slice="2/3", slices=""), 150, "", 0)
        self.assertTrue(any("slice" in l[1] and "2/3" in l[1] for l in lines))


if __name__ == "__main__":
    unittest.main()
