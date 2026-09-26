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
    *,
    baseline_quality: dict[str, Any] | None = None,
    corruption_log: dict[str, Any] | None = None,
    baseline_answers: list[dict[str, Any]] | None = None,
    corrupted_answers: list[dict[str, Any]] | None = None,
    repaired_answers: list[dict[str, Any]] | None = None,
    raw_source: Any = None,
) -> str:
    """Write the measured three-state comparison and return its console table."""
    baseline_quality = baseline_quality or {}
    corruption_log = corruption_log or {}
    baseline_freshness = baseline_quality.get("freshness", {})

    def gate(quality: dict[str, Any]) -> str:
        return "PASS" if quality.get("success") else "FAIL"

    def gx_passed(quality: dict[str, Any]) -> str:
        expectations = quality.get("expectations", [])
        return f"{sum(bool(item.get('success')) for item in expectations)}/{len(expectations)}"

    def freshness_status(freshness: dict[str, Any]) -> str:
        return "PASS" if freshness.get("is_fresh") else "FAIL"

    def row(label: str, values: tuple[Any, Any, Any]) -> str:
        return f"| {label} | {values[0]} | {values[1]} | {values[2]} |"

    table_lines = [
        "| Metric | Baseline | Corrupted | Repaired |",
        "| --- | ---: | ---: | ---: |",
        row("Records", (
            baseline_quality.get("row_count", "N/A"),
            corrupted_quality.get("row_count", "N/A"),
            repaired_quality.get("row_count", "N/A"),
        )),
        row("Evaluation questions", (
            baseline_metrics.get("samples", "N/A"),
            corrupted_metrics.get("samples", "N/A"),
            repaired_metrics.get("samples", "N/A"),
        )),
        row("Retrieval hit rate", tuple(_format_percentage(m.get("retrieval_hit_rate")) for m in (baseline_metrics, corrupted_metrics, repaired_metrics))),
        row("Mean token F1", tuple(_format_decimal(m.get("mean_token_f1")) for m in (baseline_metrics, corrupted_metrics, repaired_metrics))),
        row("Judge accuracy", tuple(_format_percentage(m.get("judge_accuracy")) for m in (baseline_metrics, corrupted_metrics, repaired_metrics))),
        row("Mean judge score / 5", tuple(_format_decimal(m.get("mean_judge_score")) for m in (baseline_metrics, corrupted_metrics, repaired_metrics))),
        row("Quality gate", tuple(gate(q) for q in (baseline_quality, corrupted_quality, repaired_quality))),
        row("GX checks passed", tuple(gx_passed(q) for q in (baseline_quality, corrupted_quality, repaired_quality))),
        row("Freshness SLA", tuple(freshness_status(f) for f in (baseline_freshness, corrupted_freshness, repaired_freshness))),
        row("Stale rows", tuple(f"{f.get('stale_rows', 'N/A')}/{f.get('total_rows', 'N/A')}" for f in (baseline_freshness, corrupted_freshness, repaired_freshness))),
        row("Stale ratio", tuple(_format_percentage(f.get("stale_ratio")) for f in (baseline_freshness, corrupted_freshness, repaired_freshness))),
    ]
    table = "\n".join(table_lines)

    scenario_lines = [
        "| Scenario | Affected rows |",
        "| --- | ---: |",
    ]
    for name, details in corruption_log.get("scenarios", {}).items():
        scenario_lines.append(f"| `{name}` | {details.get('count', 'N/A')} |")

    answer_lines = [
        "| Question | Type | Baseline hit | Corrupted hit | Repaired hit | Baseline F1 | Corrupted F1 | Repaired F1 |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    if baseline_answers is not None and corrupted_answers is not None and repaired_answers is not None:
        by_id = (
            {item["id"]: item for item in baseline_answers},
            {item["id"]: item for item in corrupted_answers},
            {item["id"]: item for item in repaired_answers},
        )
        for question_id in by_id[0]:
            if not all(question_id in answers for answers in by_id):
                continue
            states = [answers[question_id] for answers in by_id]
            hit = ["Yes" if item["retrieval_hit"] else "No" for item in states]
            scores = [_format_decimal(item["token_f1"]) for item in states]
            answer_lines.append(
                f"| {question_id} | {states[0]['question_type']} | "
                + " | ".join((*hit, *scores)) + " |"
            )

    lines = [
        "# Corruption and Idempotent Repair Report",
        "",
        "## Source and method",
        "",
        f"- Repair source: `{raw_source}`",
        "- Repaired records were rebuilt from the saved raw snapshot with the normal cleaning pipeline; corrupted records were not used as repair input.",
        "- All three evaluations use the saved baseline test set and separate vector collections.",
        "",
        "## Baseline vs Corrupted vs Repaired",
        "",
        table,
        "",
        "## Injected failures",
        "",
        "\n".join(scenario_lines),
        "",
        "## Question-level impact",
        "",
        "\n".join(answer_lines),
        "",
        "## Interpretation",
        "",
        f"- Retrieval hit rate: {_format_percentage(baseline_metrics.get('retrieval_hit_rate'))} → {_format_percentage(corrupted_metrics.get('retrieval_hit_rate'))} → {_format_percentage(repaired_metrics.get('retrieval_hit_rate'))}.",
        f"- Mean token F1: {_format_decimal(baseline_metrics.get('mean_token_f1'))} → {_format_decimal(corrupted_metrics.get('mean_token_f1'))} → {_format_decimal(repaired_metrics.get('mean_token_f1'))}.",
        f"- Quality gate: {gate(baseline_quality)} → {gate(corrupted_quality)} → {gate(repaired_quality)}.",
        "",
    ]
    write_text(report_path, "\n".join(lines))
    return table
