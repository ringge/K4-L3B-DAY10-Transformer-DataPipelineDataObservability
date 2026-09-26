from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.corruption import corrupt_clean_dataframe
from observability.quality import run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Corrupt the saved baseline, then measure its quality and RAG impact."""
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
    baseline = read_json(settings.paths.baseline_metrics)
    print(f"Corrupted data quality gate: {'PASS' if quality['success'] else 'FAIL'}")
    for name in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy"):
        print(f"{name}: {baseline[name]:.3f} -> {evaluation.summary[name]:.3f}")
    print(f"Corruption log: {settings.paths.corruption_log}")
    print(f"Corrupted metrics: {settings.paths.corrupted_metrics}")
