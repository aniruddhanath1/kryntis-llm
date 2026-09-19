"""
Kryntis AI — main entry point.

Usage:
    python main.py generate-datasets                  # Generate all synthetic datasets
    python main.py download-datasets [--domain <d>]   # Download domain dataset sources
    python main.py process-datasets [--domain <d>]    # Process datasets into clean JSONL
    python main.py train-tokenizer                    # Byte/ASCII direct mode info
    python main.py train [--domain <d>] [--resume]    # Train domain model sequentially
    python main.py train-user-input [--steps 20]      # Fine-tune model from user inputs
    python main.py train-interactive                  # Interactive training & correction loop
    python main.py evaluate                           # Evaluate model checkpoint
    python main.py serve                              # Start FastAPI / MCP / A2A server
    python main.py chat                               # Interactive CLI chat (5B context)
    python main.py ingest <path>                      # Ingest document/codebase/audio/video
"""

from __future__ import annotations

import asyncio
import argparse
import sys
from pathlib import Path


def parse_train_args(argv: list[str]) -> argparse.Namespace:
    """Parse options for one sequential custom Kryntis training run.

    Args:
        argv: Arguments following the ``train`` command.

    Returns:
        Parsed domain selection and checkpoint-resume flag.
    """
    parser = argparse.ArgumentParser(prog="python main.py train")
    parser.add_argument("--domain", help="Processed corpus domain to train, for example coding, agi, healthcare, fintech.")
    parser.add_argument("--resume", action="store_true", help="Resume the latest checkpoint.")
    return parser.parse_args(argv)


def validate_training_corpus(
    domain: str | None, data_dir: Path = Path("data/processed")
) -> Path:
    """Return a non-empty processed corpus selected for training.

    Args:
        domain: Optional domain-specific corpus name.
        data_dir: Directory containing processed JSONL corpora.

    Raises:
        FileNotFoundError: If the selected corpus is missing or contains only whitespace.
    """
    filename = f"train_corpus_{domain}.jsonl" if domain else "train_corpus.jsonl"
    corpus = data_dir / filename
    if not corpus.is_file() or not corpus.read_text(encoding="utf-8").strip():
        raise FileNotFoundError(f"Training corpus not found or empty: {corpus}")
    return corpus


def serve():
    """Start FastAPI server with uvicorn."""
    import uvicorn
    from kryntis.utils.config import get_config
    cfg = get_config().service
    uvicorn.run(
        "kryntis.service.app:app",
        host=cfg.host,
        port=cfg.port,
        reload=cfg.reload,
        log_level="info",
        access_log=True,
    )


async def _chat_loop():
    """Run interactive terminal chat with 5B session context."""
    from kryntis.orchestrator.agent_loop import AIOrchestrator, OrchestratorRequest
    print("\n🤖 Kryntis AI — Self-Hosted Interactive Chat (5B Virtual Context Engine)")
    print("Type 'exit' or 'quit' to stop.\n")
    orchestrator = AIOrchestrator()
    session_id = "cli-session"

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        req = OrchestratorRequest(session_id=session_id, user_message=user_input)
        result = await orchestrator.chat(req)
        print(f"\nKryntis AI: {result.response}\n")
        if result.citations:
            print("Sources:")
            for c in result.citations[:3]:
                print(f"  [{c.get('index', '')}] {c.get('source_path', c.get('url', ''))}")
        print()


async def _interactive_training_loop():
    """Interactive loop to teach and fine-tune model directly from user input."""
    from kryntis.learning.user_trainer import UserTrainer
    print("\n🎓 Kryntis AI — Interactive Training & Human Feedback Loop")
    print("Enter training prompt and expected answer. Type 'done' to start gradient steps.\n")
    trainer = UserTrainer()

    while True:
        try:
            prompt = input("\n[Prompt / Instruction]: ").strip()
            if prompt.lower() in ("done", "train", "exit", "quit"):
                break
            if not prompt:
                continue

            response = input("[Target Response / Correction]: ").strip()
            if not response:
                print("Empty response, skipping.")
                continue

            count = trainer.record_user_sample(prompt, response)
            print(f"✓ Recorded sample #{count} in user training corpus.")
        except (EOFError, KeyboardInterrupt):
            break

    total = trainer.count_samples()
    if total > 0:
        print(f"\nStarting fine-tuning on {total} user interaction samples...")
        result = trainer.train_on_user_data(max_steps=20)
        print(f"Training finished: {result}")
    else:
        print("No samples recorded.")


async def _ingest(path: str):
    """Ingest a file, audio, video, or codebase."""
    from pathlib import Path
    from kryntis.ingestion.pipeline import IngestionPipeline
    print(f"Ingesting with guaranteed chunking: {path}")
    pipeline = IngestionPipeline()
    job = await pipeline.ingest_files([Path(path)])
    print(f"Done. Chunks: {job.total_chunks}, Status: {job.status}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()

    from kryntis.utils.task_queue import run_heavy_task_safely

    if cmd == "generate-datasets":
        from kryntis.datasets.synthetic_generator import SyntheticDatasetGenerator
        print("Generating all local synthetic datasets across all domains...")
        gen = SyntheticDatasetGenerator()
        gen.generate_all()
        print("✓ All synthetic datasets generated in data/raw/")

    elif cmd == "download-datasets":
        from kryntis.datasets.downloader import DatasetDownloader
        domain = None
        if "--domain" in sys.argv:
            idx = sys.argv.index("--domain")
            if idx + 1 < len(sys.argv):
                domain = sys.argv[idx + 1]

        if domain:
            print(f"Downloading domain dataset: '{domain}'...")
            run_heavy_task_safely("download-datasets", DatasetDownloader().download_domain, domain=domain, required_ram_mb=800.0)
        else:
            phase = 1
            if len(sys.argv) > 3 and sys.argv[2] == "--phase":
                phase = int(sys.argv[3])
            print(f"Downloading Phase {phase} datasets...")
            run_heavy_task_safely("download-datasets", DatasetDownloader().download_all, phase=phase, required_ram_mb=800.0)

    elif cmd == "process-datasets":
        from kryntis.datasets.processor import DatasetProcessor
        domain = None
        if "--domain" in sys.argv:
            idx = sys.argv.index("--domain")
            if idx + 1 < len(sys.argv):
                domain = sys.argv[idx + 1]

        if domain:
            print(f"Processing domain dataset: '{domain}'...")
            run_heavy_task_safely("process-datasets", DatasetProcessor().process_domain, domain=domain, required_ram_mb=800.0)
        else:
            print("Processing raw datasets into clean corpus...")
            run_heavy_task_safely("process-datasets", DatasetProcessor().process_all, required_ram_mb=800.0)

    elif cmd == "train-tokenizer":
        print("Kryntis AI is running in Tokenizer-Free Byte/ASCII Direct Mode.")
        print("No tokenizer model training required! Text is directly mapped to ASCII / UTF-8 Byte values [0..255].")

    elif cmd == "train":
        from kryntis.training.trainer import Trainer
        args = parse_train_args(sys.argv[2:])
        validate_training_corpus(args.domain)

        print(
            "Training Kryntis custom model sequentially "
            f"(domain={args.domain or 'all'}, resume={args.resume})..."
        )
        run_heavy_task_safely(
            "train",
            Trainer().train,
            resume=args.resume,
            domain=args.domain,
            required_ram_mb=1500.0,
        )

    elif cmd == "train-user-input":
        from kryntis.learning.user_trainer import UserTrainer
        steps = 20
        if "--steps" in sys.argv:
            idx = sys.argv.index("--steps")
            if idx + 1 < len(sys.argv):
                steps = int(sys.argv[idx + 1])
        trainer = UserTrainer()
        print(f"Fine-tuning model from user interactions ({steps} steps)...")
        res = trainer.train_on_user_data(max_steps=steps)
        print(f"Result: {res}")

    elif cmd == "train-interactive":
        asyncio.run(_interactive_training_loop())

    elif cmd == "evaluate":
        from kryntis.training.evaluator import TrainingEvaluator
        print("Evaluating latest model checkpoint...")
        evaluator = TrainingEvaluator()
        run_heavy_task_safely("evaluate", evaluator.evaluate_checkpoint, "data/models/checkpoints/final_model.pt", required_ram_mb=1000.0)

    elif cmd == "serve":
        serve()

    elif cmd == "chat":
        asyncio.run(_chat_loop())

    elif cmd == "ingest" and len(sys.argv) > 2:
        asyncio.run(_ingest(sys.argv[2]))

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
