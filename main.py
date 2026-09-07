"""
Kryntis AI — main entry point.

Usage:
    python main.py download-datasets [--phase 1]
    python main.py process-datasets
    python main.py train-tokenizer
    python main.py train [--resume]
    python main.py evaluate
    python main.py serve          # Start FastAPI server
    python main.py chat           # Interactive CLI chat
    python main.py ingest <path>  # Ingest a document/codebase
"""

from __future__ import annotations

import sys
import asyncio


def serve():
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
    from kryntis.orchestrator.agent_loop import AIOrchestrator, OrchestratorRequest
    print("\n🤖 Kryntis Coder — Self-Hosted Interactive Chat")
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
        print(f"\nKryntis Coder: {result.response}\n")
        if result.citations:
            print("Sources:")
            for c in result.citations[:3]:
                print(f"  [{c.get('index', '')}] {c.get('source_path', c.get('url', ''))}")
        print()


async def _ingest(path: str):
    from pathlib import Path
    from kryntis.ingestion.pipeline import IngestionPipeline
    print(f"Ingesting: {path}")
    pipeline = IngestionPipeline()
    job = await pipeline.ingest_files([Path(path)])
    print(f"Done. Chunks: {job.total_chunks}, Status: {job.status}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()

    from kryntis.utils.task_queue import run_heavy_task_safely

    if cmd == "download-datasets":
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
        resume = "--resume" in sys.argv
        domain = None
        if "--domain" in sys.argv:
            idx = sys.argv.index("--domain")
            if idx + 1 < len(sys.argv):
                domain = sys.argv[idx + 1]

        print(f"Training Kryntis model sequentially (domain={domain or 'all'}, resume={resume})...")
        run_heavy_task_safely("train", Trainer().train, resume=resume, domain=domain, required_ram_mb=1500.0)

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
