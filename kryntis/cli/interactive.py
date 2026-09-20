"""Interactive teaching mode."""

from kryntis.learning.user_trainer import UserTrainer
from kryntis.cli.formatters import CLIFormatter

def run_interactive_teaching() -> None:
    trainer = UserTrainer()
    print(CLIFormatter.bold(CLIFormatter.cyan("=== Kryntis Interactive Teaching Mode ===")))
    while True:
        try:
            prompt = input(CLIFormatter.green("Prompt: ")).strip()
            if prompt.lower() == "done":
                break
            target = input(CLIFormatter.cyan("Target: ")).strip()
            if target.lower() == "done":
                break
            trainer.record_feedback(prompt, target)
        except (KeyboardInterrupt, EOFError):
            break
    trainer.train_on_feedback()
