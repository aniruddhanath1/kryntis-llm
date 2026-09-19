"""Run one validated custom Kryntis training job from the Python shell.

Usage:
    python scripts/train.py --domain coding [--resume]
"""

import argparse
import sys
from pathlib import Path

from kryntis.training.trainer import Trainer


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse sequential custom-training arguments.

    Args:
        argv: Command-line arguments after the script name.

    Returns:
        Parsed domain and resume values.
    """
    parser = argparse.ArgumentParser(prog="python scripts/train.py")
    parser.add_argument("--domain", help="Processed corpus domain to train.")
    parser.add_argument("--resume", action="store_true", help="Resume the latest checkpoint.")
    return parser.parse_args(argv)


def validate_corpus(domain: str | None) -> Path:
    """Return the selected non-empty processed JSONL corpus.

    Raises:
        FileNotFoundError: If the selected corpus does not contain training data.
    """
    filename = f"train_corpus_{domain}.jsonl" if domain else "train_corpus.jsonl"
    corpus = Path("data/processed") / filename
    if not corpus.is_file() or not corpus.read_text(encoding="utf-8").strip():
        raise FileNotFoundError(f"Training corpus not found or empty: {corpus}")
    return corpus


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    validate_corpus(args.domain)
    print(f"Starting Kryntis custom pretraining (domain={args.domain or 'all'}, resume={args.resume})...")
    trainer = Trainer()
    trainer.train(resume=args.resume, domain=args.domain)
