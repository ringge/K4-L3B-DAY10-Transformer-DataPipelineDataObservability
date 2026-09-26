from __future__ import annotations

from datetime import timedelta
from math import ceil
from pathlib import Path

import pandas as pd

from core.utils import write_json


_REQUIRED_COLUMNS = {
    "paper_id", "title", "summary", "published", "age_days",
    "authors_joined", "categories_joined", "summary_chars", "text_for_embedding",
}
_NOISE = "@@@ ### ~~~ CORRUPTED BYTES ~~~ ### @@@ "


def _embedding_text(row: pd.Series) -> str:
    return "\n".join(
        (
            f"Title: {row['title']}",
            f"Summary: {row['summary']}",
            f"Authors: {row['authors_joined']}",
            f"Categories: {row['categories_joined']}",
            f"Published: {row['published']}",
        )
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Inject six reproducible failures into a copy of a clean paper corpus."""
    missing = sorted(_REQUIRED_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(f"Corruption input missing required columns: {', '.join(missing)}")
    if len(df) < 10:
        raise ValueError("At least 10 records are required to exercise all six scenarios.")
    if df["paper_id"].isna().any() or df["paper_id"].duplicated().any():
        raise ValueError("Corruption input must contain unique, non-null paper IDs.")

    corrupted = df.copy(deep=True).reset_index(drop=True)
    dates = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    ages = pd.to_numeric(corrupted["age_days"], errors="coerce")
    if dates.isna().any() or ages.isna().any():
        raise ValueError("Corruption input requires valid published dates and numeric ages.")

    scenarios: dict[str, dict] = {}
    drop_count = ceil(len(corrupted) * 0.20)
    latest = corrupted.assign(_date=dates).sort_values(
        ["_date", "paper_id"], ascending=[False, True], kind="stable"
    ).head(drop_count)
    dropped_ids = set(latest["paper_id"])
    scenarios["drop_latest_records"] = {
        "count": drop_count,
        "fraction_of_input": drop_count / len(df),
        "changes": [
            {"paper_id": row.paper_id, "published_before": row.published, "after": None}
            for row in latest.itertuples(index=False)
        ],
    }
    corrupted = corrupted.loc[~corrupted["paper_id"].isin(dropped_ids)].copy()
    corrupted = corrupted.sort_values("paper_id", kind="stable").reset_index(drop=True)

    def change(name: str, positions: range, column: str, transform) -> None:
        changes = []
        for position in positions:
            if position >= len(corrupted):
                break
            before = corrupted.at[position, column]
            after = transform(before)
            corrupted.at[position, column] = after
            changes.append({"paper_id": corrupted.at[position, "paper_id"], "before": before, "after": after})
        scenarios[name] = {"count": len(changes), "changes": changes}

    # Stable ID bands cover the questions in the saved baseline test set.
    change("blank_summary", range(0, 2), "summary", lambda _: "")
    change("inject_noise", range(2, 5), "summary", lambda value: _NOISE + value)
    change("truncate_title", range(4, 7), "title", lambda value: value[:7])

    stale_changes = []
    for position in range(6, min(13, len(corrupted))):
        before = corrupted.at[position, "published"]
        after = (pd.Timestamp(before) - timedelta(days=730)).date().isoformat()
        age_before = int(corrupted.at[position, "age_days"])
        corrupted.at[position, "published"] = after
        corrupted.at[position, "age_days"] = age_before + 730
        stale_changes.append({
            "paper_id": corrupted.at[position, "paper_id"],
            "published_before": before,
            "published_after": after,
            "age_days_before": age_before,
            "age_days_after": age_before + 730,
        })
    scenarios["stale_date"] = {"count": len(stale_changes), "changes": stale_changes}

    corrupted["summary_chars"] = corrupted["summary"].str.len()
    corrupted["text_for_embedding"] = corrupted.apply(_embedding_text, axis=1)

    duplicate_source = corrupted.head(4).copy(deep=True)
    scenarios["duplicate_rows"] = {
        "count": len(duplicate_source),
        "changes": [
            {"paper_id": paper_id, "source_row": int(position), "duplicate_row": len(corrupted) + position}
            for position, paper_id in enumerate(duplicate_source["paper_id"])
        ],
    }
    corrupted = pd.concat([corrupted, duplicate_source], ignore_index=True)

    write_json(Path(output_log_path), {
        "input_rows": len(df),
        "output_rows": len(corrupted),
        "unique_output_papers": int(corrupted["paper_id"].nunique()),
        "scenarios": scenarios,
    })
    return corrupted
