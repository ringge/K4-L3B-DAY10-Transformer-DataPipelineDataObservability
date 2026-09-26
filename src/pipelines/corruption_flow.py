from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Corrupt, repair from the trusted raw snapshot, and compare all states."""
    settings = load_settings()
    clean_df = pd.DataFrame(read_json(settings.paths.clean_json))
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(
        corrupted_df, settings, settings.paths.corrupted_embeddings_json
    )
    quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    evaluation = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )

    raw_path = (
        settings.paths.raw_records_json
        if settings.paths.raw_records_json.exists()
        else settings.paths.raw_api_response
    )
    if not raw_path.exists():
        raise FileNotFoundError("Repair requires a saved Crossref raw snapshot.")
    repaired_df = build_clean_dataframe(load_raw_records(raw_path), now_utc())
    if repaired_df.empty:
        raise ValueError("The raw snapshot produced no repairable records.")
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, settings.paths.repaired_embeddings_json
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_evaluation = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.eval_testset,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_quality = read_json(settings.paths.baseline_quality_report)
    table = generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        evaluation.summary,
        repaired_evaluation.summary,
        quality,
        repaired_quality,
        quality["freshness"],
        repaired_quality["freshness"],
        baseline_quality=baseline_quality,
        corruption_log=read_json(settings.paths.corruption_log),
        baseline_answers=read_json(settings.paths.baseline_answers),
        corrupted_answers=evaluation.answers,
        repaired_answers=repaired_evaluation.answers,
        raw_source=raw_path.relative_to(settings.paths.project_dir).as_posix(),
    )
    print(table)
    print(f"Report: {settings.paths.comparison_report}")
