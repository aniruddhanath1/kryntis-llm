# Kryntis AI — Change Ledger

This file tracks meaningful changes to the project: architectural decisions, breaking changes, dependency upgrades, and environment/config changes. Entries are newest-first within each version block.

---

## Unreleased

_Changes not yet tagged._

---

## v3.0.0

### Architecture
- **Byte-level encoding (v3):** Replaced BPE (v1) and natural-word (v2) tokenizers with a tokenizer-free byte processor (`kryntis/core/byte_processor.py`). Vocab size is now 260 (UTF-8 bytes + special tokens). `train_tokenizer` CLI command is a no-op.
- **Hybrid RAG:** Retrieval upgraded to BM25 (sparse) + dense vector search fused with Reciprocal Rank Fusion (RRF), followed by cross-encoder reranking. Replaces single dense-only lookup from v2.
- **Three-tier memory:** Short-term ring buffer, long-term vector memory, and episodic session storage added. Background `MemoryConsolidator` runs on a 3600s interval.
- **Internet research fallback:** Added `kryntis/internet/` pipeline (DuckDuckGo + optional Brave Search) triggered when KB retrieval confidence is below threshold.
- **Continual learning pipeline:** `kryntis/learning/` added. Internet-fetched and ingested content buffered as candidates; supports human or auto approval before writing to the vector store.
- **Emotional intelligence layer:** `kryntis/core/emotional_intelligence.py` added. Regex-based emotion detection (joy, anger, sadness, frustration, curiosity) injects EQ directives into the system prompt.
- **Provider abstraction:** `kryntis/core/providers/` introduced with abstract `BaseLLMProvider` and three concrete backends: local (`.pt` + GGUF), OpenAI, Anthropic.
- **FastAPI service:** `kryntis/service/` added. Four router groups: chat, ingestion, knowledge, admin.

### Config
- All settings migrated to `pydantic-settings` classes with per-subsystem env prefixes (see `kryntis/utils/config.py`).
- `config/default.yaml` added as YAML default layer.

### Data
- Training domains expanded: added `healthcare` (epfl-llm/meditron-dataset) and `security` (Kali/THC toolsets).

### Breaking Changes
- `.env.example` keys have changed to match new pydantic-settings prefixes. Rename old keys accordingly (see `WALKTHROUGH.md` — Configuration section).
- `KRYNTIS_MODEL_PATH` now accepts both `.pt` PyTorch checkpoints and `.gguf` llama-cpp model files.

---

## v2.0.0

### Architecture
- **Natural-word tokenizer (v2):** Added `kryntis/core/word_tokenizer.py` as an intermediate step between BPE (v1) and byte-level (v3). Now superseded.
- **ChromaDB integration:** Replaced in-memory FAISS-only store with ChromaDB as the default disk-persistent backend.
- **pgvector support:** Optional PostgreSQL + pgvector adapter added for production deployments.
- **Document ingestion pipeline:** Added multi-format chunkers for PDF, DOCX, PPTX, XLSX, HTML, JSON, code, and images (OCR).

### Dependencies
- Added `chromadb`, `PyMuPDF`, `python-docx`, `python-pptx`, `openpyxl`, `pytesseract`.

---

## v1.0.0

### Architecture
- Initial implementation: custom GPT-style decoder Transformer trained from scratch.
- BPE tokenizer (`kryntis/core/tokenizer.py`, `tokenizer_trainer.py`).
- FAISS-based vector store for retrieval.
- Basic CLI: `download-datasets`, `process-datasets`, `train`, `evaluate`, `chat`.

### Domains
- Initial training domains: `english`, `regional_languages`, `emotion`, `coding`, `crm`, `sysadmin`.

---

## How to Add an Entry

When making a significant change:

1. Add it under **Unreleased** in the appropriate category below.
2. On release, rename the block to the new version number and date.

Categories to use:
- **Architecture** — new subsystems, removed subsystems, changed data flows
- **API** — new endpoints, removed endpoints, changed request/response shapes
- **Config** — new/removed/renamed environment variables or YAML keys
- **Dependencies** — added/removed/upgraded packages
- **Data** — new training domains, dataset sources, tokenizer changes
- **Breaking Changes** — anything requiring consumer code or env changes
- **Bug Fixes** — notable correctness fixes
