from __future__ import annotations

from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from typing import Iterable

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


_OUTPUT_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "age_days",
    "text_for_embedding",
]


class _MarkupTextExtractor(HTMLParser):
    """Extract readable text while preserving boundaries around block tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower().split(":")[-1] in {"p", "br", "li"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower().split(":")[-1] in {"p", "li"}:
            self.parts.append(" ")


def _clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    parser = _MarkupTextExtractor()
    parser.feed(value)
    parser.close()
    return normalize_whitespace(unescape("".join(parser.parts)))


def _clean_items(values: Iterable[object] | object) -> list[str]:
    if values is None:
        return []
    candidates = [values] if isinstance(values, str) else values
    try:
        cleaned = (_clean_text(value) for value in candidates)
        return list(dict.fromkeys(value for value in cleaned if value))
    except TypeError:
        return []


def _as_utc_timestamp(value: object) -> pd.Timestamp | None:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed)


def _normalize_run_date(run_date: datetime) -> pd.Timestamp:
    timestamp = pd.Timestamp(run_date)
    if pd.isna(timestamp):
        raise ValueError("run_date must be a valid datetime.")
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize Crossref records into a deterministic embedding-ready dataframe."""
    run_timestamp = _normalize_run_date(run_date)
    clean_rows: list[dict[str, object]] = []
    seen_paper_ids: set[str] = set()

    for record in records:
        paper_id = _clean_text(record.paper_id)
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)
        if not paper_id or not title or not summary:
            continue

        published_timestamp = _as_utc_timestamp(record.published)
        if published_timestamp is None:
            continue

        deduplication_key = paper_id.casefold()
        if deduplication_key in seen_paper_ids:
            continue

        updated_timestamp = _as_utc_timestamp(record.updated)
        if updated_timestamp is None:
            updated_timestamp = published_timestamp
        authors = _clean_items(record.authors)
        categories = _clean_items(record.categories)
        primary_category = _clean_text(record.primary_category)
        if not primary_category and categories:
            primary_category = categories[0]

        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        published = published_timestamp.date().isoformat()
        updated = updated_timestamp.date().isoformat()
        age_days = (run_timestamp - published_timestamp).days
        text_for_embedding = "\n".join(
            [
                f"Title: {title}",
                f"Summary: {summary}",
                f"Authors: {authors_joined}",
                f"Categories: {categories_joined}",
                f"Published: {published}",
            ]
        )

        clean_rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": _clean_text(record.abs_url),
                "pdf_url": _clean_text(record.pdf_url),
                "comment": _clean_text(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )
        seen_paper_ids.add(deduplication_key)

    clean_df = pd.DataFrame(clean_rows, columns=_OUTPUT_COLUMNS)
    if clean_df.empty:
        return clean_df
    return clean_df.sort_values("paper_id", kind="stable").reset_index(drop=True)
