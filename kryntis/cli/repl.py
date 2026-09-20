"""Interactive REPL loop."""

from kryntis.cli.formatters import CLIFormatter
from kryntis.orchestrator.agent_loop import default_agent_loop

class TerminalREPL:
    def __init__(self, session_id: str = "cli-interactive") -> None:
        self.session_id = session_id

    def run(self) -> None:
        print(CLIFormatter.bold(CLIFormatter.cyan("=== Kryntis AI Sovereign REPL ===")))
        while True:
            try:
                prompt = input(CLIFormatter.green("kryntis> ")).strip()
                if not prompt:
                    continue
                if prompt.lower() in ("exit", "quit", "q"):
                    break
                response = default_agent_loop.run_turn(
                    user_prompt=prompt,
                    session_id=self.session_id
                )
                print(f"\n{response.get('response', '')}\n")
            except (KeyboardInterrupt, EOFError):
                break
