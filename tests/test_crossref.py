from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import requests

from core.config import load_settings
from core.utils import read_json, write_json
from ingestion.crossref import fetch_source_records, load_raw_records, parse_crossref_payload


def _response(status: int, payload: dict | None = None) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(payload or {}).encode()
    response.url = "https://api.crossref.org/works"
    return response


def _payload() -> dict:
    return {
        "message": {
            "items": [
                {
                    "DOI": "10.1234/example",
                    "title": ["  A <i>paper</i>  "],
                    "abstract": "<jats:p>First &amp; second.</jats:p><jats:p>More text.</jats:p>",
                    "author": [{"given": " Ada ", "family": " Lovelace "}],
                    "subject": [" Computing ", "Computing"],
                    "published": {"date-parts": [[2026, 6]]},
                    "deposited": {"date-time": "2026-07-04T10:00:00Z"},
                    "link": [{"content-type": "application/pdf", "URL": "https://example.org/paper.pdf"}],
                },
                {"DOI": "10.1234/incomplete", "title": ["Missing abstract"]},
            ]
        }
    }


class CrossrefTests(unittest.TestCase):
    def test_parse_normalizes_metadata_and_skips_incomplete_items(self) -> None:
        records = parse_crossref_payload(_payload())
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.title, "A paper")
        self.assertEqual(record.summary, "First & second. More text.")
        self.assertEqual(record.authors, ["Ada Lovelace"])
        self.assertEqual(record.categories, ["Computing"])
        self.assertEqual(record.published, "2026-06-01")
        self.assertEqual(record.updated, "2026-07-04")
        self.assertEqual(record.abs_url, "https://doi.org/10.1234/example")
        self.assertEqual(record.pdf_url, "https://example.org/paper.pdf")

    def test_refresh_retries_then_saves_both_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            settings = replace(load_settings(Path(directory)), refresh_source=True)
            with patch("ingestion.crossref.requests.get", side_effect=[
                _response(429), _response(503), _response(200, _payload())
            ]) as get, patch("ingestion.crossref.time.sleep") as sleep:
                records = fetch_source_records(settings)

            self.assertEqual(len(records), 1)
            self.assertEqual(get.call_count, 3)
            self.assertEqual(get.call_args.kwargs["params"], {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            })
            self.assertEqual(sleep.call_count, 2)
            self.assertEqual(read_json(settings.paths.raw_api_response), _payload())
            self.assertEqual(load_raw_records(settings.paths.raw_records_json), records)

    def test_refresh_uses_snapshot_after_network_failure(self) -> None:
        with TemporaryDirectory() as directory:
            settings = replace(load_settings(Path(directory)), refresh_source=True)
            write_json(settings.paths.raw_api_response, _payload())
            with patch("ingestion.crossref.requests.get", side_effect=requests.ConnectionError("offline")) as get, \
                    patch("ingestion.crossref.time.sleep"):
                records = fetch_source_records(settings)

            self.assertEqual(get.call_count, 3)
            self.assertEqual(len(records), 1)
            self.assertEqual(load_raw_records(settings.paths.raw_records_json), records)

    def test_refresh_uses_snapshot_after_repeated_rate_limits(self) -> None:
        with TemporaryDirectory() as directory:
            settings = replace(load_settings(Path(directory)), refresh_source=True)
            write_json(settings.paths.raw_api_response, _payload())
            with patch("ingestion.crossref.requests.get", side_effect=[_response(429)] * 3) as get, \
                    patch("ingestion.crossref.time.sleep"):
                records = fetch_source_records(settings)

            self.assertEqual(get.call_count, 3)
            self.assertEqual(len(records), 1)
            self.assertEqual(read_json(settings.paths.raw_api_response), _payload())

    def test_invalid_payload_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "items list"):
            parse_crossref_payload({"message": {}})
