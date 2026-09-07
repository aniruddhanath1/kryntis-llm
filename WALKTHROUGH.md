# Kryntis AI — Project Walkthrough

## What Is This?

Kryntis is a fully self-hosted AI platform built around a custom GPT-style decoder Transformer trained from scratch. It exposes a FastAPI service consumed by a Java Spring Boot backend and a React frontend. The model runs locally with no mandatory cloud dependency; OpenAI and Anthropic providers are available as optional fallbacks.

---

## High-Level Architecture

```
React Frontend
      │
      ▼
Java Spring Boot (calls Kryntis over HTTP with X-Kryntis-Key)
      │
      ▼
FastAPI Service  ──► RAG Pipeline ──► Vector Store (Chroma / FAISS / pgvector)
      │                                   ▲
      ▼                                   │
AI Orchestrator ──► Local LLM ──► Ingestion Pipeline
      │
      ▼
Internet Research (DuckDuckGo / Brave)
```

The orchestrator is the central brain. For every chat request it:

1. Runs the emotional intelligence (EQ) layer to detect user sentiment and adjust the system prompt tone.
2. Routes intent (RAG lookup, internet search, direct inference, task planning).
3. Retrieves relevant chunks from the knowledge base using hybrid BM25 + dense retrieval + cross-encoder reranking.
4. Falls back to internet research if retrieval confidence is low.
5. Builds the full prompt and calls the active LLM provider.
6. Updates short-term, long-term, and episodic memory.

---

## Repository Layout

```
kryntis-llm-local/
├── main.py                    # CLI entry point — all commands here
├── config/
│   ├── default.yaml           # YAML defaults for every subsystem
│   └── logging.yaml           # structlog + rotating file handler
├── data/
│   ├── models/checkpoints/    # Trained PyTorch checkpoints (.pt)
│   ├── processed/             # Cleaned JSONL training corpora (per domain)
│   ├── raw/                   # Raw downloaded datasets
│   └── tokenizer/             # Tokenizer vocab files (legacy BPE, v1/v2)
├── kryntis/                   # Main Python package
│   ├── core/                  # Model, inference engine, providers
│   ├── orchestrator/          # Agent loop, intent router, prompt builder
│   ├── rag/                   # Embedder, retriever, reranker, context builder
│   ├── chunking/              # Per-format document chunkers
│   ├── ingestion/             # Upload → parse → chunk → embed → store pipeline
│   ├── knowledge/             # Vector store adapters + SQLite metadata
│   ├── memory/                # Short-term, long-term, episodic memory
│   ├── internet/              # Search → fetch → extract → cite pipeline
│   ├── learning/              # Continual learning (candidate approval flow)
│   ├── security/              # Prompt injection guard, output sanitizer, rate limiter
│   ├── datasets/              # Dataset catalog, downloader, processor, synthetic gen
│   ├── training/              # Pretraining loop, dataset loader, evaluator
│   ├── evaluation/            # RAG hallucination / confidence evaluator
│   ├── service/               # FastAPI app, DI, routers
│   └── utils/                 # Config loader, logging, memory monitor, streaming
└── scripts/
    ├── download_datasets.py
    └── train.py
```

---

## Core Subsystems

### 1. Model (`kryntis/core/model.py`)

A custom decoder-only Transformer with:
- RMSNorm, RoPE positional encoding
- Grouped-Query Attention (GQA)
- SwiGLU feed-forward network
- Parameter range: 10M – 350M (default config targets ~25M, safe within 8 GB RAM)

**Tokenization:** The current version (v3) is tokenizer-free. Text is encoded directly as UTF-8 bytes (vocab size = 260). Legacy BPE (v1) and natural-word (v2) tokenizers exist in `core/tokenizer*.py` but are not used at inference time.

### 2. Providers (`kryntis/core/providers/`)

| Provider | Class | Backend |
|---|---|---|
| Local | `LocalProvider` | PyTorch `.pt` checkpoint or llama-cpp GGUF |
| OpenAI | `OpenAIProvider` | GPT-4o / GPT-4o-mini |
| Anthropic | `AnthropicProvider` | Claude (any model) |

`model_manager.py` currently locks to the local provider. Switch providers by setting `KRYNTIS_MODEL_BACKEND`.

### 3. RAG Pipeline (`kryntis/rag/`)

- **Embedder:** `sentence-transformers` `all-MiniLM-L6-v2` (384-dim)
- **Retrieval:** hybrid BM25 (sparse) + dense vector search, fused with Reciprocal Rank Fusion (RRF)
- **Reranker:** cross-encoder for final relevance scoring
- **Context builder:** assembles retrieved chunks + inline citations

### 4. Knowledge Store (`kryntis/knowledge/`)

| Adapter | Use case |
|---|---|
| ChromaDB | Default, disk-persistent, no extra infra |
| FAISS | In-memory, fastest for pure vector search |
| pgvector | Production PostgreSQL-backed store |

SQLite (via `aiosqlite`) stores document metadata and provenance alongside the vector store.

### 5. Document Ingestion (`kryntis/ingestion/`, `kryntis/chunking/`)

Supported formats: PDF (PyMuPDF), DOCX, PPTX, XLSX/XLS, HTML, JSON, plain text, code files, images (OCR via pytesseract).

Flow: upload → MIME validation → format-specific chunker → embedder → vector store + SQLite.

### 6. Memory (`kryntis/memory/`)

| Tier | Implementation | Capacity |
|---|---|---|
| Short-term | In-process ring buffer | 20 turns / 2048 tokens (configurable) |
| Long-term | Semantic vector search | Unlimited (disk-backed) |
| Episodic | Session episode records | Unlimited |

A background `MemoryConsolidator` runs every 3600s to compress and promote short-term memories to long-term.

### 7. Internet Research (`kryntis/internet/`)

When knowledge-base retrieval confidence is low, the orchestrator triggers:
1. DuckDuckGo search (or Brave if `BRAVE_SEARCH_API_KEY` is set)
2. HTTP page fetch + readability extraction
3. Content scoring and domain trust validation
4. Citation formatting and provenance tracking

Enable/disable with `KRYNTIS_INTERNET_ENABLED`.

### 8. Continual Learning (`kryntis/learning/`)

Internet-fetched and ingested content is buffered as learning candidates. Candidates above a confidence threshold are either auto-approved or queued for human review (controlled by `KRYNTIS_LEARNING_REQUIRE_APPROVAL`). Approved batches are written back to the vector store.

### 9. Security (`kryntis/security/`)

- Prompt injection detection (`prompt_guard.py`)
- Response sanitization (`output_sanitizer.py`)
- In-process rate limiter: 60 requests/minute (configurable)

---

## API Reference

All endpoints are under the FastAPI service (default `http://localhost:8000`). Internal auth is enforced via the `X-Kryntis-Key` header.

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe |
| POST | `/api/v1/chat/message` | Non-streaming chat |
| POST | `/api/v1/chat/stream` | SSE streaming chat |
| GET | `/api/v1/chat/session/{id}` | Fetch session memory |
| DELETE | `/api/v1/chat/session/{id}` | Delete session |
| POST | `/api/v1/ingestion/upload` | Upload files to knowledge base |
| GET | `/api/v1/ingestion/job/{id}` | Poll ingestion job status |
| DELETE | `/api/v1/ingestion/source/{id}` | Remove a source |
| GET | `/api/v1/knowledge/sources` | List ingested sources |
| GET | `/api/v1/knowledge/search` | Search the knowledge base |
| GET | `/api/v1/knowledge/stats` | KB chunk/source counts |
| POST | `/api/v1/knowledge/snapshot` | Create a KB snapshot |
| GET | `/api/v1/knowledge/snapshots` | List snapshots |
| GET | `/api/v1/admin/health` | Full system health |
| GET | `/api/v1/admin/providers` | Provider status |
| GET | `/api/v1/admin/learning/pending` | Learning candidates queue |
| POST | `/api/v1/admin/learning/approve/{id}` | Approve a candidate |
| POST | `/api/v1/admin/learning/process` | Run learning batch |

---

## CLI Commands

```bash
# Dataset pipeline
python main.py download-datasets [--phase 1|2] [--domain <name>]
python main.py process-datasets  [--domain <name>]

# Training
python main.py train    [--resume] [--domain <name>]
python main.py evaluate

# Service
python main.py serve     # FastAPI on 0.0.0.0:8000

# Direct interaction
python main.py chat      # Interactive CLI
python main.py ingest <path>   # Ingest a file or directory
```

---

## Configuration System

Config is loaded in two layers (later overrides earlier):

1. `config/default.yaml` — YAML defaults for all subsystems
2. Environment variables (from `.env` or shell) — per-class prefixed overrides

### Environment Variable Prefixes

| Prefix | Subsystem |
|---|---|
| `KRYNTIS_SERVICE_` | FastAPI host/port/log level |
| `KRYNTIS_MODEL_` | Model path, backend, threads, GPU layers, temperature |
| `KRYNTIS_RAG_` | Embedder model, top-k, BM25/dense weights |
| `KRYNTIS_CHUNKING_` | Chunk size, overlap |
| `KRYNTIS_KNOWLEDGE_` | Vector backend, Chroma path, SQLite path, collection name |
| `KRYNTIS_MEMORY_` | Short-term limits, consolidation interval |
| `KRYNTIS_INGESTION_` | Max files per batch, max file size, upload dir |
| `KRYNTIS_INTERNET_` | Enabled flag, search engine, max results, timeout |
| `KRYNTIS_LEARNING_` | Enabled flag, confidence threshold, require approval |
| `KRYNTIS_SECURITY_` | Injection detection, max prompt length, rate limit |

Top-level (no prefix):

- `KRYNTIS_INTERNAL_KEY` — shared secret for `X-Kryntis-Key` header auth
- `BRAVE_SEARCH_API_KEY` — optional Brave Search API key

---

## Training Domains

| Domain | Description |
|---|---|
| `english` | Natural language and grammar |
| `regional_languages` | World languages and multilingual text |
| `emotion` | Emotional intelligence and sentiment |
| `coding` | Software engineering and code |
| `crm` | Enterprise CRM (Salesforce, SAP, Dynamics, ServiceNow, HubSpot) |
| `sysadmin` | Shell scripting, PowerShell, MDM |
| `security` | Cybersecurity tools and concepts |
| `healthcare` | Medical QA |

---

## Key Dependencies

| Category | Package |
|---|---|
| ML framework | `torch >= 2.2`, `transformers >= 4.40`, `accelerate >= 0.30` |
| Local inference | `llama-cpp-python >= 0.2.70` |
| Embeddings | `sentence-transformers >= 2.7` |
| Vector DB | `chromadb >= 0.5`, `faiss-cpu >= 1.7` |
| Sparse retrieval | `rank-bm25 >= 0.2` |
| Web framework | `fastapi >= 0.111`, `uvicorn[standard] >= 0.29` |
| Config | `pydantic-settings >= 2.2`, `python-dotenv >= 1.0` |
| Logging | `structlog >= 24.1`, `rich >= 13.7` |
| File parsing | `PyMuPDF`, `python-docx`, `python-pptx`, `openpyxl`, `pytesseract` |

Full list: `requirements.txt` (production), `requirements-dev.txt` (dev/test).

---

## Getting Started

```bash
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and configure environment
copy .env.example .env        # Windows
cp .env.example .env          # Linux/macOS
# Edit .env — set KRYNTIS_INTERNAL_KEY at minimum

# 4. Start the service
python main.py serve

# 5. Verify
curl http://localhost:8000/health
```
