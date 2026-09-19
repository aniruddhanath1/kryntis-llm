# Kryntis AI — Architecture & Implementation Plan

## Current Target: Version 1.0.0 (Production Release)

### Core Architecture Highlights

1. **Tokenizer-Free Byte / ASCII Direct Architecture (`ByteDirectProcessor`)**:
   - Maps text directly to UTF-8 / ASCII byte integers (0–255) and binary representations with a fixed vocabulary size of 260 tokens (256 bytes + 4 control tokens).
   - Eliminates subword dictionaries, external tokenizers, and subword splitting overhead.

2. **SOLID Persistence Layer & Repository Pattern (`kryntis/repositories/`)**:
   - Clean separation of concerns following SOLID principles.
   - Abstract interfaces: `IRepository`, `IDocumentRepository`, `ISessionRepository`, `IKnowledgeRepository`.
   - Concrete persistent SQLite and in-memory implementations.

3. **Dynamic Model Load Balancers (`kryntis/core/load_balancer.py`)**:
   - `RoundRobinLoadBalancer`, `WeightedLoadBalancer`, and `LeastLatencyLoadBalancer` for distributing inference requests across local instances and providers.

4. **Multi-Strategy Rate Limiters (`kryntis/security/rate_limiter.py`)**:
   - `TokenBucketRateLimiter` (burst capacity and smooth token replenishment).
   - `SlidingWindowRateLimiter` (precise rolling-window request tracking).
   - `MultiTierRateLimiter` (hierarchical client IP + session rate limiting).

5. **Virtual 5B Single-Session Context Stream (`kryntis/memory/session_context_manager.py`)**:
   - Decouples raw prompt context limits from overall session state.
   - Manages up to 5,000,000,000 max context state per session via SQLite disk storage, streaming event pagination, and hierarchical semantic chunk retrieval.

6. **Guaranteed Universal Chunking (`kryntis/chunking/chunk_router.py`)**:
   - All text inputs, file uploads, continual learning items, and audio/video assets route through `ChunkRouter`.
   - Audio (.mp3, .wav, .flac, .ogg, .m4a, .aac) and Video (.mp4, .mkv, .avi, .mov, .webm) chunkers enforce a strict **10 MB max** limit.
   - Document chunkers enforce a **100 MB max** limit.

7. **Voice Synthesis & Transcription Engine (`kryntis/voice/`)**:
   - `TextToSpeechEngine` (native harmonic formant wave synthesizer + pyttsx3 fallback).
   - `SpeechToTextEngine` (acoustic feature decoder + SpeechRecognition fallback).
   - End-to-end voice assistant conversation pipeline.

8. **Extensible AI Tool Registry (`kryntis/tools/`)**:
   - Dynamic tool registration with OpenAI Function Calling & MCP schema export.
   - 9 built-in sandboxed tools: `code_interpreter`, `calculator`, `fs_read_file`, `fs_list_dir`, `web_fetch`, `sql_query`, `http_request`, `system_info`, and `analyze_media`.

9. **14 Sector Pretraining Domains & Synthetic Datasets (`kryntis/datasets/`)**:
   - Domains: `agi`, `coding` (40+ world languages), `healthcare`, `fintech`, `military`, `government`, `media`, `crm`, `sysadmin`, `security`, `english`, `regional_languages`, and `emotion`.
   - Local synthetic JSONL generators generating standalone training corpora in `data/raw/` and `data/processed/`.

10. **Interactive OpenAPI / Swagger Documentation (`kryntis/service/app.py`)**:
    - Swagger UI (`/docs`), ReDoc (`/redoc`), and OpenAPI 3.1 schema.

---

## 5-Year Model Release Roadmap

| Year | Model Release Name | Architectural Focus |
|---|---|---|
| **2026** | **Kryntis 1.0 Genesis** | Sovereign Multi-Domain Core, 5B Virtual Session Context, Full AI Tooling & Voice |
| **2027** | **Kryntis 2.0 Aether** | Multimodal Streaming Sensory Matrix, Real-time Audio-Visual Synthesis |
| **2028** | **Kryntis 3.0 Synapse** | Autonomous Hierarchical Reasoning, Meta-Cognition, Dynamic Symbolic AGI |
| **2029** | **Kryntis 4.0 Quantum** | Entangled Polyglot Architecture, Universal Code Execution & Self-Correction |
| **2030** | **Kryntis 5.0 Omnis** | Universal Sovereign General Intelligence, Zero-Latency Federated Edge Agents |

---

## Build & Sequential Training Commands

```bash
# 1. Generate Local Synthetic Datasets across all 14 domains
python main.py generate-datasets

# 2. Process Domain Datasets into Clean JSONL Corpora
python main.py process-datasets --domain coding
python main.py process-datasets --domain agi
python main.py process-datasets --domain healthcare
python main.py process-datasets --domain fintech
python main.py process-datasets --domain military
python main.py process-datasets --domain government
python main.py process-datasets --domain media

# 3. Train Sequentially via Python Shell (No Ollama Required)
python main.py train --domain coding
python main.py train --domain agi
python main.py train --domain healthcare
python main.py train --domain fintech
python main.py train --domain military
python main.py train --domain government
python main.py train --domain media

# 4. Interactive Human Teaching & Fine-Tuning
python main.py train-interactive
python main.py train-user-input

# 5. Serve Standalone Local API with Swagger UI
python main.py serve
```

---

## Historical Version Archive

### Version 3.0 (Historical)
- Tokenizer-Free Byte / ASCII Direct Architecture (`ByteDirectProcessor`).
- Hybrid RAG: BM25 + dense vector retrieval with RRF + cross-encoder reranking.
- Three-tier memory with consolidator.
- Internet research fallback (DuckDuckGo + Brave Search).
- Continual learning confidence-gated pipeline.

### Version 2.0 (Historical)
- Natural-word tokenizer (`NaturalEnglishTokenizer`).
- ChromaDB disk persistence.
- pgvector PostgreSQL adapter.
- Multi-format document ingestion pipeline (PDF, DOCX, PPTX, XLSX, HTML, JSON, code, images).

### Version 1.0 (Historical)
- Initial scratch decoder Transformer with BPE tokenization.
