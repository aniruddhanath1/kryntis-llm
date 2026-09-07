# Kryntis LLM

A tokenizer-free, self-learning LLM platform built from scratch in Python — designed for
memory-efficient local inference, continual learning, retrieval-augmented generation (RAG),
and multimodal knowledge ingestion.

---

## Features

- **Custom Transformer (v3)** — byte-level decoder, vocab size 260, 10M–350M parameters
- **Hybrid RAG** — BM25 + dense vector retrieval with Reciprocal Rank Fusion, cross-encoder reranking
- **Three-tier memory** — short-term ring buffer, long-term ChromaDB/FAISS/pgvector, episodic sessions
- **Multi-provider LLM** — local `.pt` / GGUF (llama-cpp), OpenAI, Anthropic — all behind one interface
- **Continual learning** — confidence-gated knowledge ingestion with optional human approval
- **MCP server** — Model Context Protocol 2025-03-26, JSON-RPC 2.0 at `/mcp`
- **A2A protocol** — Google Agent-to-Agent interoperability at `/a2a`, Agent Card at `/.well-known/agent.json`
- **Guardrails** — prompt-injection detection, toxic-input blocking, PII scrubbing, harmful-output blocking
- **Internet research** — DuckDuckGo / Brave Search with citation tracking and trust scoring
- **Full ingestion pipeline** — PDF, DOCX, PPTX, XLSX, HTML, images (OCR), JSON, plain text

---

## Requirements

- Python **3.10** or later
- [Ollama](https://ollama.com) (for base model serving, optional but recommended)
- [Tesseract](https://github.com/tesseract-ocr/tesseract) (optional, for OCR on image files)
- PostgreSQL with [pgvector](https://github.com/pgvector/pgvector) (production only; dev uses ChromaDB)

---

## Clone the repository

### macOS / Linux — SSH

```bash
# 1. Generate an SSH key if you don't have one
ssh-keygen -t ed25519 -C "your@email.com"

# 2. Add the public key to your GitHub account
#    Settings → SSH and GPG keys → New SSH key
cat ~/.ssh/id_ed25519.pub

# 3. Clone
git clone git@github.com:<your-org>/kryntis-llm.git
cd kryntis-llm
```

### Windows — SSH (PowerShell)

```powershell
# 1. Generate an SSH key (PowerShell runs OpenSSH built into Windows 10/11)
ssh-keygen -t ed25519 -C "your@email.com"
# Key is saved to C:\Users\<you>\.ssh\id_ed25519

# 2. Copy the public key to clipboard
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | Set-Clipboard
# Paste it in GitHub → Settings → SSH and GPG keys → New SSH key

# 3. Test the connection
ssh -T git@github.com

# 4. Clone
git clone git@github.com:<your-org>/kryntis-llm.git
cd kryntis-llm
```

> **Tip (Windows):** If `ssh-keygen` is not found, enable the OpenSSH client:
> Settings → Apps → Optional Features → Add a feature → OpenSSH Client

---

## Setup

### macOS / Linux

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# (Development extras — linting, testing)
pip install -r requirements-dev.txt
```

### Windows (PowerShell)

```powershell
# Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# If execution policy blocks scripts, run once as administrator:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# (Development extras)
pip install -r requirements-dev.txt
```

---

## Environment configuration

Environment files are **encrypted** in this repo. See [ENV_ENCRYPTION.md](ENV_ENCRYPTION.md)
for the full encrypt/decrypt workflow. Quick start:

```bash
# 1. Obtain the key from your team's secrets store and place it here:
#    <repo-root>/.env-encryption.key

# 2. Decrypt the environment file for your target environment
python -c "
from cryptography.fernet import Fernet; from pathlib import Path
f = Fernet(Path('.env-encryption.key').read_bytes())
Path('.env-develop').write_bytes(f.decrypt(Path('.env-develop.enc').read_bytes()))
print('done')
"
```

Available environments: `develop` · `qa` · `stage` · `prod`

---

## Run the API server

```bash
# Activate your venv first (see Setup above)

# Development — auto-reload, debug logging, localhost only
python main.py --env develop

# Staging / Production — load the decrypted env file explicitly
python main.py --env stage
```

The API will be available at:

| Endpoint | Description |
|---|---|
| `http://localhost:8000/docs` | Interactive Swagger UI |
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/api/chat` | Chat (POST) |
| `http://localhost:8000/api/knowledge` | Knowledge base management |
| `http://localhost:8000/mcp` | MCP server (JSON-RPC 2.0) |
| `http://localhost:8000/a2a` | A2A agent endpoint |
| `http://localhost:8000/.well-known/agent.json` | A2A Agent Card (public) |

Authentication: pass `X-Kryntis-Key: <your-key>` on all `/api/*`, `/mcp*`, and `/a2a` requests.

---

## Download a base model via Ollama

Kryntis delegates to [Ollama](https://ollama.com) for serving base models.

```bash
# Install Ollama
# macOS
brew install ollama

# Windows — download the installer from https://ollama.com/download

# Pull a model (pick one based on your VRAM / RAM)
ollama pull tinyllama:1.1b-chat      # 0.67 GB — fastest, low RAM
ollama pull qwen2.5:1.5b             # 0.99 GB
ollama pull gemma2:2b                # 1.60 GB
ollama pull llama3.2:3b              # 2.00 GB
ollama pull phi3:mini                # 2.30 GB
ollama pull codellama:7b-instruct    # 3.80 GB — best for code tasks
ollama pull mistral:7b-instruct      # 4.10 GB — best general purpose

# Start Ollama (runs as a background service)
ollama serve
```

Then set `KRYNTIS_MODEL_BACKEND=ollama` and `KRYNTIS_MODEL_PATH=<model-tag>` in your env file.

---

## Train a custom Kryntis model

The training pipeline fine-tunes or trains the custom v3 Transformer on domain-specific data.

### 1. Download and prepare datasets

```bash
# Download all registered GitHub datasets
python scripts/download_datasets.py

# Datasets are saved to data/raw/ and preprocessed into data/processed/
```

### 2. Configure training

Edit `kryntis/training/config.py` or pass overrides on the command line.
Key parameters:

| Parameter | Default | Description |
|---|---|---|
| `--model-size` | `small` | `small` (10M) · `medium` (70M) · `large` (350M) |
| `--domain` | `general` | `general` · `coding` · `crm` · `security` · `sysadmin` · `multilingual` |
| `--epochs` | `3` | Number of training epochs |
| `--batch-size` | `32` | Batch size per GPU/CPU |
| `--lr` | `3e-4` | Learning rate |
| `--checkpoint-dir` | `data/models/checkpoints` | Where to save `.pt` checkpoints |

### 3. Run training

```bash
# macOS / Linux
python scripts/train.py \
  --domain general \
  --model-size small \
  --epochs 3 \
  --checkpoint-dir data/models/checkpoints

# Windows (PowerShell)
python scripts/train.py `
  --domain general `
  --model-size small `
  --epochs 3 `
  --checkpoint-dir data/models/checkpoints
```

With GPU acceleration (NVIDIA CUDA):

```bash
KRYNTIS_MODEL_GPU_LAYERS=32 python scripts/train.py --domain coding --model-size medium
```

### 4. Evaluate

```bash
python -c "
from kryntis.evaluation.rag_evaluator import RAGEvaluator
# see kryntis/evaluation/rag_evaluator.py for full API
"
```

Checkpoints are saved to `data/models/checkpoints/` after each epoch. The final model is
`final_model.pt`. Point `KRYNTIS_MODEL_PATH` to it in your env file to serve it.

---

## Ingest documents into the knowledge base

```bash
# Via the REST API (server must be running)
curl -X POST http://localhost:8000/api/ingestion/upload \
  -H "X-Kryntis-Key: <your-key>" \
  -F "files=@report.pdf" \
  -F "files=@notes.docx"

# Via the MCP tool (from any MCP-compatible client)
# Tool: kryntis.ingest_text
# Params: { "text": "...", "source": "manual", "domain": "general" }
```

Supported file types: PDF, DOCX, PPTX, XLSX, XLS, TXT, CSV, HTML, JSON, XML, JPEG, PNG, GIF, WEBP

---

## Project structure

```
kryntis-llm/
├── kryntis/
│   ├── chunking/        # Document chunkers (PDF, DOCX, code, HTML, …)
│   ├── core/            # Custom Transformer, tokenizer, inference, model manager
│   │   └── providers/   # LLM provider abstraction (local, OpenAI, Anthropic)
│   ├── datasets/        # Dataset catalog, downloader, processor, synthetic generator
│   ├── evaluation/      # RAG evaluator
│   ├── ingestion/       # File ingestion pipeline and validator
│   ├── internet/        # Web search, fetch, citation builder
│   ├── knowledge/       # Vector store, document store, pgvector adapter
│   ├── learning/        # Continual learning and versioning
│   ├── memory/          # Short-term, long-term, episodic memory
│   ├── orchestrator/    # Agent loop, intent router, prompt builder, task planner
│   ├── rag/             # Embedder, retriever (BM25 + dense + RRF), reranker
│   ├── security/        # Guardrails, prompt guard, output sanitizer, rate limiter
│   ├── service/         # FastAPI app, middleware, routers (chat, admin, MCP, A2A)
│   ├── training/        # Trainer, dataset loader, evaluator, config
│   └── utils/           # Config, cache, logging, streaming, task queue
├── scripts/
│   ├── download_datasets.py
│   └── train.py
├── config/
│   ├── default.yaml     # Base config for all settings
│   └── logging.yaml     # Logging config
├── .env-*.enc           # Encrypted environment files (safe to commit)
├── .env.example         # Template — copy and fill in values
├── ENV_ENCRYPTION.md    # How to encrypt / decrypt env files
├── WALKTHROUGH.md       # Full developer reference and architecture guide
├── LEDGER.md            # Chronological changelog
├── main.py              # Entry point
├── pyproject.toml
└── requirements.txt
```

---

## Developer reference

See [WALKTHROUGH.md](WALKTHROUGH.md) for the full architecture diagram, all API endpoints,
config prefix table, training domains, and a getting-started quickstart.

See [LEDGER.md](LEDGER.md) for the project changelog.

---

## License

MIT
