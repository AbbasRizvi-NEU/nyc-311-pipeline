import json
import tempfile
import unittest
from pathlib import Path

from pipeline import load_requests


class PipelineTest(unittest.TestCase):
    def test_repeat_load_and_closure_change_the_median(self):
        demo = json.loads(Path("demo.json").read_text(encoding="utf-8"))
        update = json.loads(Path("demo-update.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "requests.duckdb"
            initial = load_requests(db, demo)
            self.assertEqual(initial["inserted"], 3)
            self.assertEqual(initial["by_problem"][0]["median_hours_to_close"], 4)
            repeat = load_requests(db, demo)
            self.assertEqual((repeat["inserted"], repeat["updated"], repeat["unchanged"]), (0, 0, 3))
            changed = load_requests(db, update)
            self.assertEqual((changed["inserted"], changed["updated"]), (0, 1))
            self.assertEqual(changed["by_problem"][0]["median_hours_to_close"], 6)

    def test_invalid_batch_leaves_existing_data_intact(self):
        demo = json.loads(Path("demo.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "requests.duckdb"
            load_requests(db, demo)
            with self.assertRaises(ValueError):
                load_requests(db, [demo[0], demo[0]])
            self.assertEqual(load_requests(db, [])["by_problem"][0]["requests"], 3)
