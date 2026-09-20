"""CLI Parser for kryntis."""

import argparse

def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kryntis",
        description="Kryntis AI Sovereign LLM Platform"
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("serve", help="Start FastAPI REST & Swagger server")
    subparsers.add_parser("chat", help="Start interactive terminal chat REPL")
    subparsers.add_parser("generate-datasets", help="Generate synthetic pretraining datasets")
    return parser
