import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from ingestion.corruption import corrupt_clean_dataframe
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.reporting import generate_corruption_report


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

    def test_repair_rebuilds_from_raw_even_after_corruption(self) -> None:
        root = Path(__file__).resolve().parents[1]
        raw_path = root / "data/raw/crossref_records.json"
        run_date = datetime(2026, 9, 26, tzinfo=UTC)
        clean = build_clean_dataframe(load_raw_records(raw_path), run_date)
        with TemporaryDirectory() as directory:
            corrupt_clean_dataframe(clean, Path(directory) / "corruption.json")
        repaired = build_clean_dataframe(load_raw_records(raw_path), run_date)
        pd.testing.assert_frame_equal(clean, repaired)
        self.assertEqual(repaired["paper_id"].nunique(), len(repaired))

    def test_report_contains_three_measured_states(self) -> None:
        metrics = [
            {"samples": 10, "retrieval_hit_rate": hit, "mean_token_f1": hit,
             "judge_accuracy": hit, "mean_judge_score": 5 * hit}
            for hit in (1.0, 0.6, 1.0)
        ]
        quality = [
            {"success": success, "row_count": rows, "expectations": [{"success": success}],
             "freshness": {"is_fresh": success, "stale_rows": 0 if success else 7,
                           "total_rows": rows, "stale_ratio": 0 if success else 0.3}}
            for success, rows in ((True, 24), (False, 23), (True, 24))
        ]
        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.md"
            table = generate_corruption_report(
                report_path, *metrics, quality[1], quality[2],
                quality[1]["freshness"], quality[2]["freshness"],
                baseline_quality=quality[0], raw_source="raw.json",
            )
            report = report_path.read_text(encoding="utf-8")
        self.assertIn("| Metric | Baseline | Corrupted | Repaired |", table)
        self.assertIn("| Retrieval hit rate | 100.0% | 60.0% | 100.0% |", report)
        self.assertIn("| Quality gate | PASS | FAIL | PASS |", report)
        self.assertIn("- Repair source: `raw.json`", report)


if __name__ == "__main__":
    unittest.main()
