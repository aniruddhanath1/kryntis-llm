"""Tests for kryntis.cli subsystem."""

import pytest
from kryntis.cli import build_cli_parser, CLIFormatter

def test_cli_parser_commands():
    parser = build_cli_parser()
    args = parser.parse_args(["serve"])
    assert args.command == "serve"

    args = parser.parse_args(["chat"])
    assert args.command == "chat"

def test_cli_formatter():
    styled = CLIFormatter.cyan("test-text")
    assert "test-text" in styled
    assert CLIFormatter.OKCYAN in styled
