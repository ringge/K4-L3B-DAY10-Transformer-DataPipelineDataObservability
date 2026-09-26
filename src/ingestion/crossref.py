from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import logging
from pathlib import Path
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


_CROSSREF_URL = "https://api.crossref.org/works"
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


class _TextExtractor(HTMLParser):
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
    parser = _TextExtractor()
    parser.feed(value)
    return normalize_whitespace(unescape("".join(parser.parts)))


def _first_text(value: object) -> str:
    if isinstance(value, list):
        return next((text for entry in value if (text := _clean_text(entry))), "")
    return _clean_text(value)


def _crossref_date(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    parts = value.get("date-parts")
    if isinstance(parts, list) and parts and isinstance(parts[0], list):
        try:
            year, *rest = parts[0]
            return date(year, rest[0] if rest else 1, rest[1] if len(rest) > 1 else 1).isoformat()
        except (TypeError, ValueError):
            pass
    date_time = value.get("date-time")
    if isinstance(date_time, str):
        try:
            return date.fromisoformat(date_time[:10]).isoformat()
        except ValueError:
            pass
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Convert a Crossref works response to usable paper records."""
    if not isinstance(payload, dict) or not isinstance(payload.get("message"), dict):
        raise ValueError("Invalid Crossref payload: missing message object")
    items = payload["message"].get("items")
    if not isinstance(items, list):
        raise ValueError("Invalid Crossref payload: missing items list")

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        doi = _clean_text(item.get("DOI"))
        title = _first_text(item.get("title"))
        summary = _clean_text(item.get("abstract"))
        published = next(
            (day for key in ("published", "published-online", "published-print", "created")
             if (day := _crossref_date(item.get(key)))),
            "",
        )
        if not all((doi, title, summary, published)):
            continue

        authors: list[str] = []
        author_entries = item.get("author")
        for author in author_entries if isinstance(author_entries, list) else []:
            if not isinstance(author, dict):
                continue
            name = normalize_whitespace(" ".join(filter(None, (
                _clean_text(author.get("given")), _clean_text(author.get("family"))
            )))) or _clean_text(author.get("name"))
            if name:
                authors.append(name)

        subjects = item.get("subject")
        categories = [_clean_text(subject) for subject in subjects] if isinstance(subjects, list) else []
        categories = list(dict.fromkeys(category for category in categories if category))
        updated = next(
            (day for key in ("deposited", "updated", "created")
             if (day := _crossref_date(item.get(key)))),
            published,
        )
        abs_url = _clean_text(item.get("URL")) or f"https://doi.org/{doi}"
        links = item.get("link")
        pdf_url = next(
            (_clean_text(link.get("URL")) for link in links
             if isinstance(link, dict) and link.get("content-type") == "application/pdf"
             and _clean_text(link.get("URL"))),
            abs_url,
        ) if isinstance(links, list) else abs_url
        records.append(PaperRecord(
            paper_id=doi,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=categories[0] if categories else "",
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=f"Crossref record {doi}",
        ))
    return records


def _retry_delay(response: requests.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return min(max(float(retry_after), 0), 30)
        except ValueError:
            try:
                return min(max(parsedate_to_datetime(retry_after).timestamp() - time.time(), 0), 30)
            except (TypeError, ValueError, OverflowError):
                pass
    return float(2 ** attempt)


def _download_payload(settings: Settings) -> dict:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    failure: Exception | None = None
    for attempt in range(3):
        delay = float(2 ** attempt)
        try:
            response = requests.get(_CROSSREF_URL, params=params, timeout=20)
            response.raise_for_status()
            payload = response.json()
            if not parse_crossref_payload(payload):
                raise ValueError("Crossref returned no usable records")
            return payload
        except requests.HTTPError as exc:
            failure = exc
            status = exc.response.status_code if exc.response is not None else None
            if status not in _RETRY_STATUSES:
                raise
            delay = _retry_delay(response, attempt)
        except requests.RequestException as exc:
            failure = exc
        if attempt < 2:
            time.sleep(delay)
    raise RuntimeError("Crossref request failed after three attempts") from failure


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Load the local snapshot, or refresh it from Crossref with retry and fallback."""
    snapshot = settings.paths.raw_api_response
    if snapshot.exists() and not settings.refresh_source:
        payload = read_json(snapshot)
    else:
        try:
            payload = _download_payload(settings)
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            if not snapshot.exists():
                raise RuntimeError("Could not fetch Crossref data and no local snapshot is available") from exc
            _LOG.warning("Crossref fetch failed; using local snapshot: %s", exc)
            payload = read_json(snapshot)
        else:
            write_json(snapshot, payload)

    records = parse_crossref_payload(payload)
    if not records:
        raise ValueError("Crossref payload contains no usable records")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read saved records, or parse a saved Crossref response."""
    payload = read_json(path)
    if isinstance(payload, dict):
        return parse_crossref_payload(payload)
    if not isinstance(payload, list):
        raise ValueError("Raw records must be a list or a Crossref response")
    return [PaperRecord(**entry) for entry in payload]
