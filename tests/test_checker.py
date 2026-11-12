import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from checker import check_file


class TestXerChecker(unittest.TestCase):
    def test_schedules(self):
        b4 = check_file(BASE_DIR / "schedules" / "borouge4_industrial_plant.xer")
        self.assertEqual(len(b4["broken_rows"]), 0)
        self.assertEqual(b4["total_tasks"], 64)
        self.assertEqual(len(b4["missing_links"]), 22)
        self.assertEqual(len(b4["negative_float"]), 5)
        self.assertEqual(len(b4["high_float"]), 5)

        hp = check_file(BASE_DIR / "schedules" / "harbour_pointe_assisted_living.xer")
        self.assertEqual(len(hp["broken_rows"]), 0)
        self.assertEqual(hp["total_tasks"], 131)
        self.assertEqual(len(hp["missing_links"]), 5)
        self.assertEqual(len(hp["negative_float"]), 0)
        self.assertEqual(len(hp["high_float"]), 86)

    def test_broken_rows(self):
        broken = check_file(BASE_DIR / "tests" / "broken_sample.xer")
        self.assertEqual(len(broken["broken_rows"]), 5)
        reasons = [r for _, _, r in broken["broken_rows"]]
        self.assertTrue(any("expected 9 columns, got 6" in r for r in reasons))
        self.assertTrue(any("invalid number in total_float_hr_cnt: 'TBD'" in r for r in reasons))
        self.assertTrue(any("duplicate task_id '1001'" in r for r in reasons))
        self.assertTrue(any("invalid date" in r for r in reasons))
        self.assertTrue(any("references missing task" in r for r in reasons))


if __name__ == "__main__":
    unittest.main()
