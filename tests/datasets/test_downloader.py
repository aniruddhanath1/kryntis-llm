"""Tests for static dataset-source manifest generation."""

import json
import tempfile
import unittest
from pathlib import Path

from kryntis.datasets.catalog import DatasetSource
from kryntis.datasets.downloader import DatasetDownloader


class TestDownloader(unittest.TestCase):

    def test_write_manifest_records_catalog_and_existing_outputs(self) -> None:
        """A manifest preserves catalog provenance for a real local artifact."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            raw = tmp_path / "raw"
            artifact = raw / "sample.jsonl"
            artifact.parent.mkdir(parents=True)
            artifact.write_text('{"text": "sample"}\n', encoding="utf-8")
            source = DatasetSource("sample", "Sample", "coding", "synthetic", str(artifact), ["python"])

            manifest = DatasetDownloader(str(raw)).write_manifest(source, [artifact])
            record = json.loads(manifest.read_text(encoding="utf-8"))

            self.assertEqual(record["source_id"], "sample")
            self.assertEqual(record["output_paths"], [str(artifact)])

    def test_write_manifest_rejects_missing_output(self) -> None:
        """No manifest can claim an artifact that does not exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source = DatasetSource("sample", "Sample", "coding", "synthetic", "missing", ["python"])

            with self.assertRaises(FileNotFoundError):
                DatasetDownloader(str(tmp_path)).write_manifest(source, [tmp_path / "missing.jsonl"])


if __name__ == "__main__":
    unittest.main()
