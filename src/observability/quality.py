from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


def _quality_report_path(settings: Settings, report_name: str) -> Path:
    normalized_name = report_name.strip().lower()
    if normalized_name == "baseline":
        return settings.paths.baseline_quality_report
    if normalized_name == "corrupted":
        return settings.paths.corrupted_quality_report
    return settings.paths.quality_dir / f"{safe_slug(report_name)}_quality_report.json"


def _freshness_report_path(settings: Settings, report_name: str) -> Path:
    if report_name.strip().lower() == "baseline":
        return settings.paths.freshness_report
    return settings.paths.quality_dir / f"{safe_slug(report_name)}_freshness_report.json"


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the baseline GX checks and combine them with the freshness SLA."""
    if not report_name.strip():
        raise ValueError("report_name must not be empty.")

    try:
        context = gx.get_context(mode="ephemeral")
        data_source = context.data_sources.add_pandas(name="papers_source")
        data_asset = data_source.add_dataframe_asset(name="papers_asset")
        batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
        batch = batch_def.get_batch(batch_parameters={"dataframe": df})

        expectations = [
            gx.expectations.ExpectTableRowCountToBeBetween(min_value=1),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="summary"),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
            gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
            gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=50),
        ]
        expectation_results = [
            batch.validate(expectation, result_format="SUMMARY").to_json_dict()
            for expectation in expectations
        ]
    except Exception as exc:
        raise RuntimeError(
            f"Great Expectations validation failed for report '{report_name}': {exc}"
        ) from exc

    freshness = build_freshness_report(
        df,
        settings,
        _freshness_report_path(settings, report_name),
    )
    payload = {
        "report_name": report_name,
        "success": all(bool(result["success"]) for result in expectation_results)
        and bool(freshness["is_fresh"]),
        "row_count": len(df),
        "expectations": expectation_results,
        "freshness": freshness,
    }
    write_json(_quality_report_path(settings, report_name), payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Calculate and persist the document-freshness SLA summary."""
    required_columns = {"published", "age_days"}
    missing_columns = sorted(required_columns.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Freshness report missing required columns: {', '.join(missing_columns)}")

    ages = pd.to_numeric(df["age_days"], errors="coerce")
    if ages.isna().any():
        raise ValueError("Freshness report requires numeric, non-null age_days values.")

    published_dates = pd.to_datetime(df["published"], errors="coerce", utc=True)
    if published_dates.isna().any():
        raise ValueError("Freshness report requires valid, non-null published dates.")

    total_rows = len(df)
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 0.0
    payload = {
        "latest_published": (
            published_dates.max().date().isoformat() if total_rows else None
        ),
        "oldest_published": (
            published_dates.min().date().isoformat() if total_rows else None
        ),
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "is_fresh": stale_ratio <= 0.25,
    }
    write_json(Path(report_path), payload)
    return payload
