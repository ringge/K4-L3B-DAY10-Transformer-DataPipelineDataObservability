from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


_REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "categories_joined",
    "published",
}
_QUESTION_TYPES = (
    "summary",
    "summary",
    "summary",
    "authors",
    "authors",
    "authors",
    "date",
    "date",
    "categories",
    "categories",
)


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic, metadata-grounded evaluation set."""
    if df.empty:
        raise ValueError("Cannot build test set from an empty dataframe.")

    missing_columns = sorted(_REQUIRED_COLUMNS.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    if len(df) < 10:
        raise ValueError(f"At least 10 documents are required; received {len(df)}.")

    selected = df.sort_values("paper_id", kind="stable").head(10)
    test_set: list[dict[str, Any]] = []

    for position, ((_, row), question_type) in enumerate(
        zip(selected.iterrows(), _QUESTION_TYPES, strict=True),
        start=1,
    ):
        paper_id = str(row["paper_id"])
        title = str(row["title"])

        if question_type == "summary":
            question = f"What is the paper '{title}' about?"
            ground_truth = first_sentence(str(row["summary"]))
        elif question_type == "authors":
            question = f"Who authored '{title}'?"
            ground_truth = str(row["authors_joined"])
        elif question_type == "date":
            question = f"When was '{title}' published?"
            ground_truth = str(row["published"])
        else:
            question = f"What categories are associated with '{title}'?"
            ground_truth = str(row["categories_joined"])

        test_set.append(
            {
                "id": f"test-{position:02d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    if len(test_set) != 10:
        raise RuntimeError("Test set generation did not produce exactly 10 cases.")
    if len({item["id"] for item in test_set}) != 10:
        raise RuntimeError("Test set IDs must be unique.")
    if {item["question_type"] for item in test_set} != set(_QUESTION_TYPES):
        raise RuntimeError("Test set must cover summary, authors, date, and categories.")

    write_json(Path(output_path), test_set)
    return test_set
