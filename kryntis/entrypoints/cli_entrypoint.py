"""CLI Entrypoint implementation."""

import sys
from kryntis.cli.parser import build_cli_parser
from kryntis.cli.repl import TerminalREPL

def main_cli() -> None:
    parser = build_cli_parser()
    args = parser.parse_args()
    if args.command == "chat" or not args.command:
        repl = TerminalREPL()
        repl.run()
    else:
        print(f"Executed CLI command: {args.command}")

if __name__ == "__main__":
    main_cli()
