import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from ingestion.corruption import corrupt_clean_dataframe


class CorruptionTests(unittest.TestCase):
    def test_six_scenarios_keep_derived_fields_and_audit_log_consistent(self) -> None:
        clean_path = Path(__file__).resolve().parents[1] / "data/clean/papers_clean.json"
        clean = pd.DataFrame(json.loads(clean_path.read_text(encoding="utf-8")))
        original = clean.copy(deep=True)

        with TemporaryDirectory() as directory:
            log_path = Path(directory) / "corruption.json"
            corrupted = corrupt_clean_dataframe(clean, log_path)
            log = json.loads(log_path.read_text(encoding="utf-8"))

        pd.testing.assert_frame_equal(clean, original)
        self.assertEqual(len(log["scenarios"]), 6)
        self.assertEqual(log["scenarios"]["drop_latest_records"]["count"], 5)
        self.assertEqual(len(corrupted), len(clean) - 5 + 4)
        self.assertEqual(corrupted["paper_id"].duplicated().sum(), 4)

        for name, scenario in log["scenarios"].items():
            self.assertGreater(scenario["count"], 0, name)
            self.assertEqual(scenario["count"], len(scenario["changes"]))
        for row in corrupted.itertuples(index=False):
            self.assertEqual(row.summary_chars, len(row.summary))
            self.assertIn(f"Title: {row.title}\nSummary: {row.summary}", row.text_for_embedding)
            self.assertIn(f"Published: {row.published}", row.text_for_embedding)
        self.assertTrue(any(len(title) < 8 for title in corrupted["title"]))
        self.assertTrue(any(summary == "" for summary in corrupted["summary"]))
        self.assertTrue(any("CORRUPTED BYTES" in summary for summary in corrupted["summary"]))


if __name__ == "__main__":
    unittest.main()
