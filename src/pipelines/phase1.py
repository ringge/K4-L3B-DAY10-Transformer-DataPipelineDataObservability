from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run the clean-data baseline pipeline and persist its artifacts."""
    settings = load_settings()
    run_timestamp = now_utc()
    records = fetch_source_records(settings)
    clean_df = build_clean_dataframe(records, run_timestamp)

    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(clean_df, settings)
    build_test_set(clean_df, settings.paths.eval_testset)
    evaluation = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    quality = run_data_quality_checks(clean_df, settings, "baseline")
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "records_loaded": len(records),
        "records_cleaned": len(clean_df),
        "run_at_utc": run_timestamp.isoformat(),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary,
        evaluation.summary,
        quality,
        quality["freshness"],
    )

    print(f"Baseline pipeline complete: {len(clean_df)} clean records")
    print(f"Retrieval hit rate: {evaluation.summary['retrieval_hit_rate']:.3f}")
    print(f"Mean token F1: {evaluation.summary['mean_token_f1']:.3f}")
    print(f"Report: {settings.paths.baseline_report}")
