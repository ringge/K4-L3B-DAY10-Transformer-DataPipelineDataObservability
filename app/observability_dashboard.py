from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

import pandas as pd
import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.config import Settings, load_settings  # noqa: E402
from core.utils import read_json  # noqa: E402


@dataclass(frozen=True)
class StateArtifactPaths:
    data: Path
    metrics: Path
    quality: Path
    freshness: Path


@dataclass
class StateSnapshot:
    name: str
    metrics: dict[str, Any]
    quality: dict[str, Any]
    freshness: dict[str, Any]
    dataframe: pd.DataFrame | None
    issues: list[str]

    @property
    def record_count(self) -> int | None:
        value = self.quality.get("row_count")
        if isinstance(value, int):
            return value
        return len(self.dataframe) if self.dataframe is not None else None


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_DIR).as_posix()
    except ValueError:
        return str(path)


def _read_json_artifact(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, f"Missing artifact: {_relative(path)}"
    try:
        return read_json(path), None
    except (OSError, ValueError, TypeError) as exc:
        return None, f"Cannot read {_relative(path)}: {type(exc).__name__}: {exc}"


def _artifact_paths(settings: Settings) -> dict[str, StateArtifactPaths]:
    quality_dir = settings.paths.quality_dir
    return {
        "Baseline": StateArtifactPaths(
            data=settings.paths.clean_json,
            metrics=settings.paths.baseline_metrics,
            quality=settings.paths.baseline_quality_report,
            freshness=settings.paths.freshness_report,
        ),
        "Corrupted": StateArtifactPaths(
            data=settings.paths.corrupted_clean_json,
            metrics=settings.paths.corrupted_metrics,
            quality=settings.paths.corrupted_quality_report,
            freshness=quality_dir / "corrupted_freshness_report.json",
        ),
        "Repaired": StateArtifactPaths(
            data=settings.paths.repaired_clean_json,
            metrics=settings.paths.repaired_metrics,
            quality=quality_dir / "repaired_quality_report.json",
            freshness=quality_dir / "repaired_freshness_report.json",
        ),
    }


def _load_snapshot(name: str, paths: StateArtifactPaths) -> StateSnapshot:
    issues: list[str] = []

    metrics_payload, issue = _read_json_artifact(paths.metrics)
    if issue:
        issues.append(issue)
    metrics = metrics_payload if isinstance(metrics_payload, dict) else {}
    if metrics_payload is not None and not isinstance(metrics_payload, dict):
        issues.append(f"Invalid metrics format: {_relative(paths.metrics)}")

    quality_payload, issue = _read_json_artifact(paths.quality)
    if issue:
        issues.append(issue)
    quality = quality_payload if isinstance(quality_payload, dict) else {}
    if quality_payload is not None and not isinstance(quality_payload, dict):
        issues.append(f"Invalid quality report format: {_relative(paths.quality)}")

    freshness_payload, issue = _read_json_artifact(paths.freshness)
    if issue:
        issues.append(issue)
    if isinstance(freshness_payload, dict):
        freshness = freshness_payload
    elif isinstance(quality.get("freshness"), dict):
        freshness = quality["freshness"]
    else:
        freshness = {}
        if freshness_payload is not None:
            issues.append(f"Invalid freshness report format: {_relative(paths.freshness)}")

    data_payload, issue = _read_json_artifact(paths.data)
    if issue:
        issues.append(issue)
        dataframe = None
    else:
        try:
            dataframe = pd.DataFrame(data_payload)
        except (TypeError, ValueError) as exc:
            dataframe = None
            issues.append(
                f"Cannot build dataframe from {_relative(paths.data)}: "
                f"{type(exc).__name__}: {exc}"
            )

    return StateSnapshot(
        name=name,
        metrics=metrics,
        quality=quality,
        freshness=freshness,
        dataframe=dataframe,
        issues=issues,
    )


def _status_label(value: Any) -> str:
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    return "N/A"


def _number(value: Any, decimals: int = 3) -> str:
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def _percentage(value: Any) -> str:
    try:
        return f"{float(value):.1%}"
    except (TypeError, ValueError):
        return "N/A"


def _show_state_kpis(snapshot: StateSnapshot) -> None:
    st.subheader(snapshot.name)
    quality_success = snapshot.quality.get("success")
    freshness_success = snapshot.freshness.get("is_fresh")

    if quality_success is True:
        st.success("Quality Gate: PASS")
    elif quality_success is False:
        st.error("Quality Gate: FAIL")
    else:
        st.warning("Quality Gate: N/A")

    if freshness_success is True:
        st.success("Freshness SLA: PASS")
    elif freshness_success is False:
        st.error("Freshness SLA: FAIL")
    else:
        st.warning("Freshness SLA: N/A")

    st.metric("Records", snapshot.record_count if snapshot.record_count is not None else "N/A")
    st.metric("Retrieval hit rate", _percentage(snapshot.metrics.get("retrieval_hit_rate")))
    st.metric("Mean token F1", _number(snapshot.metrics.get("mean_token_f1")))
    st.metric("Judge accuracy", _percentage(snapshot.metrics.get("judge_accuracy")))
    st.metric("Stale rows", snapshot.freshness.get("stale_rows", "N/A"))
    st.metric("Stale ratio", _percentage(snapshot.freshness.get("stale_ratio")))
    st.caption(f"is_fresh: {freshness_success if freshness_success is not None else 'N/A'}")


def _comparison_frame(snapshots: list[StateSnapshot]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "State": snapshot.name,
                "Quality Gate": _status_label(snapshot.quality.get("success")),
                "Freshness SLA": _status_label(snapshot.freshness.get("is_fresh")),
                "Records": snapshot.record_count,
                "Retrieval hit rate": _percentage(
                    snapshot.metrics.get("retrieval_hit_rate")
                ),
                "Mean token F1": _number(snapshot.metrics.get("mean_token_f1")),
                "Judge accuracy": _percentage(snapshot.metrics.get("judge_accuracy")),
                "Stale rows": snapshot.freshness.get("stale_rows"),
                "Stale ratio": _percentage(snapshot.freshness.get("stale_ratio")),
                "is_fresh": snapshot.freshness.get("is_fresh"),
            }
            for snapshot in snapshots
        ]
    )


def _age_distribution(snapshots: list[StateSnapshot]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for snapshot in snapshots:
        if snapshot.dataframe is None or "age_days" not in snapshot.dataframe.columns:
            continue
        ages = pd.to_numeric(snapshot.dataframe["age_days"], errors="coerce").dropna()
        if ages.empty:
            continue
        frames.append(pd.DataFrame({"State": snapshot.name, "age_days": ages}))
    if not frames:
        return pd.DataFrame(columns=["State", "age_days"])
    return pd.concat(frames, ignore_index=True)


def _show_age_chart(age_data: pd.DataFrame, threshold: int) -> None:
    if age_data.empty:
        st.info(
            "No age_days data is available. Run `python script/run_phase1.py` and "
            "`python script/run_corruption_flow.py`, then refresh artifacts."
        )
        return

    chart_spec = {
        "layer": [
            {
                "mark": {"type": "bar", "opacity": 0.55},
                "encoding": {
                    "x": {
                        "field": "age_days",
                        "type": "quantitative",
                        "bin": {"maxbins": 24},
                        "title": "Document age (days)",
                    },
                    "y": {
                        "aggregate": "count",
                        "type": "quantitative",
                        "stack": None,
                        "title": "Record count",
                    },
                    "color": {
                        "field": "State",
                        "type": "nominal",
                        "scale": {
                            "domain": ["Baseline", "Corrupted", "Repaired"],
                            "range": ["#2563eb", "#dc2626", "#16a34a"],
                        },
                    },
                    "tooltip": [
                        {"field": "State", "type": "nominal"},
                        {"aggregate": "count", "type": "quantitative", "title": "Records"},
                    ],
                },
            },
            {
                "mark": {
                    "type": "rule",
                    "color": "#f59e0b",
                    "strokeWidth": 3,
                    "strokeDash": [8, 5],
                },
                "encoding": {
                    "x": {"datum": threshold, "type": "quantitative"},
                },
            },
        ]
    }
    st.vega_lite_chart(age_data, chart_spec, width="stretch")
    st.caption(f"Orange reference line: freshness threshold = {threshold} days")


def _show_alerts(snapshots: list[StateSnapshot]) -> None:
    found_alert = False
    for snapshot in snapshots:
        if snapshot.quality.get("success") is False:
            st.error(f"{snapshot.name}: Quality Gate failed.")
            found_alert = True
        if snapshot.freshness.get("is_fresh") is False:
            st.error(f"{snapshot.name}: Freshness SLA failed.")
            found_alert = True
    if not found_alert:
        st.success("No quality or freshness failures were found in the loaded artifacts.")


def main() -> None:
    st.set_page_config(page_title="Data Observability Dashboard", layout="wide")
    settings = load_settings(PROJECT_DIR)
    snapshots = [
        _load_snapshot(name, paths)
        for name, paths in _artifact_paths(settings).items()
    ]

    st.title("Data Observability & Drift Monitor")
    st.caption("Live view of pipeline artifacts; no sample metrics are generated by this app.")

    if st.button("Refresh artifacts", type="primary"):
        st.rerun()

    st.header("Pipeline overview")
    columns = st.columns(3)
    for column, snapshot in zip(columns, snapshots, strict=True):
        with column:
            _show_state_kpis(snapshot)

    st.header("Baseline vs Corrupted vs Repaired")
    st.dataframe(_comparison_frame(snapshots), width="stretch", hide_index=True)

    st.header("Document age distribution")
    _show_age_chart(_age_distribution(snapshots), settings.freshness_threshold_days)

    st.header("Alerts")
    _show_alerts(snapshots)

    all_issues = [issue for snapshot in snapshots for issue in snapshot.issues]
    if all_issues:
        with st.expander("Missing or invalid artifacts", expanded=True):
            for issue in all_issues:
                st.warning(issue)
            st.code(
                "python script/run_phase1.py\n"
                "python script/run_corruption_flow.py",
                language="powershell",
            )


if __name__ == "__main__":
    main()
