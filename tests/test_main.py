"""Tests for Python-command training input validation."""

from pathlib import Path
import unittest

from main import parse_train_args, validate_training_corpus


class TestMainValidation(unittest.TestCase):

    def test_parse_train_args_accepts_one_domain(self) -> None:
        """Training accepts one selected custom corpus domain."""
        args = parse_train_args(["--domain", "coding", "--resume"])
        self.assertEqual(args.domain, "coding")
        self.assertTrue(args.resume)

    def test_validate_training_corpus_returns_domain_file(self) -> None:
        """A populated selected corpus is available to the trainer."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            corpus = tmp_path / "train_corpus_coding.jsonl"
            corpus.write_text('{"text": "print(1)"}\n', encoding="utf-8")
            self.assertEqual(validate_training_corpus("coding", tmp_path), corpus)

    def test_validate_training_corpus_rejects_missing_file(self) -> None:
        """Missing selected corpora stop training before model construction."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with self.assertRaises(FileNotFoundError):
                validate_training_corpus("coding", tmp_path)

    def test_validate_training_corpus_rejects_whitespace_only_file(self) -> None:
        """Whitespace-only corpora cannot start a training run."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            corpus = tmp_path / "train_corpus_coding.jsonl"
            corpus.write_text(" \n\t", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                validate_training_corpus("coding", tmp_path)


if __name__ == "__main__":
    unittest.main()
