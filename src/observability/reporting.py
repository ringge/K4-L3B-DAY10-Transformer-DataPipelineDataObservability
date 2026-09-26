from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline run summary, evaluation metrics, and quality status."""
    expectations = quality.get("expectations", [])
    passed_expectations = sum(bool(item.get("success")) for item in expectations)
    retrieval_hit_rate = metrics.get("retrieval_hit_rate")
    mean_token_f1 = metrics.get("mean_token_f1")
    judge_accuracy = metrics.get("judge_accuracy")
    mean_judge_score = metrics.get("mean_judge_score")

    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Run Summary",
        "",
        "| Item | Value |",
        "| --- | --- |",
        f"| Source | {source_summary.get('source_api', 'N/A')} |",
        f"| Query | {source_summary.get('source_query', 'N/A')} |",
        f"| Filter | {source_summary.get('source_filter', 'N/A')} |",
        f"| Records loaded | {source_summary.get('records_loaded', 'N/A')} |",
        f"| Records cleaned | {source_summary.get('records_cleaned', 'N/A')} |",
        f"| Run time (UTC) | {source_summary.get('run_at_utc', 'N/A')} |",
        "",
        "## Baseline Evaluation",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Samples | {metrics.get('samples', 'N/A')} |",
        f"| Retrieval hit rate | {_format_percentage(retrieval_hit_rate)} |",
        f"| Mean token F1 | {_format_decimal(mean_token_f1)} |",
        f"| Judge accuracy | {_format_percentage(judge_accuracy)} |",
        f"| Mean judge score | {_format_decimal(mean_judge_score)} / 5 |",
        "",
        "## Data Quality and Freshness",
        "",
        f"- Quality gate: **{'PASS' if quality.get('success') else 'FAIL'}**",
        f"- GX expectations passed: {passed_expectations}/{len(expectations)}",
        f"- Freshness SLA: **{'PASS' if freshness.get('is_fresh') else 'FAIL'}**",
        f"- Latest published: {freshness.get('latest_published') or 'N/A'}",
        f"- Oldest published: {freshness.get('oldest_published') or 'N/A'}",
        f"- Stale records: {freshness.get('stale_rows', 'N/A')}/{freshness.get('total_rows', 'N/A')} ({_format_percentage(freshness.get('stale_ratio'))})",
        "",
        "## Artifacts",
        "",
        "- `data/clean/papers_clean.csv` and `data/clean/papers_clean.json`",
        "- `data/chroma/` baseline vector collection",
        "- `data/eval/test_set.json`",
        "- `data/results/baseline_metrics.json` and `data/results/baseline_answers.json`",
        "- `data/quality/baseline_quality_report.json` and `data/quality/freshness_report.json`",
        "",
    ]
    ragas = metrics.get("ragas", {})
    if isinstance(ragas, dict) and ragas.get("skipped"):
        lines.extend([f"Ragas: {ragas['skipped']}", ""])
    write_text(report_path, "\n".join(lines))


def _format_percentage(value: Any) -> str:
    try:
        return f"{float(value):.1%}"
    except (TypeError, ValueError):
        return "N/A"


def _format_decimal(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "N/A"


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
