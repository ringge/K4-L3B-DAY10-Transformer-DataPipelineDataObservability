from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from core.config import load_settings
from core.utils import write_json
from retrieval.index import LocalEmbeddingIndex


class IndexManifestTests(unittest.TestCase):
    def test_relative_and_legacy_absolute_persist_paths_load(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            settings = load_settings(root)
            manifest = root / "manifest.json"
            expected_path = root / "data/chroma"

            for stored_path in ("data/chroma", str(expected_path)):
                with self.subTest(stored_path=stored_path):
                    write_json(manifest, {
                        "persist_path": stored_path,
                        "collection_name": "test-collection",
                        "documents": [],
                    })
                    with patch("retrieval.index.MiniLMEmbeddings"), patch(
                        "retrieval.index.chromadb.PersistentClient"
                    ) as client:
                        index = LocalEmbeddingIndex.load(settings, manifest)
                    self.assertEqual(index.persist_path, expected_path)
                    client.assert_called_once_with(path=str(expected_path))


if __name__ == "__main__":
    unittest.main()
