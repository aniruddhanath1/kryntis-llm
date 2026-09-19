# Kryntis AI — Change Ledger

This file tracks meaningful changes to the project: architectural decisions, breaking changes, dependency upgrades, and environment/config changes. Entries are newest-first within each version block.

---

## v1.0.0 (Production Release)

### Architecture & Cognitive Reasoning
- **KV-Cache Autoregressive Acceleration**: Implemented `KVCache` in `kryntis/core/model.py` and updated `GroupedQueryAttention` to maintain cached Key-Value state tensors across incremental token decoding steps, eliminating redundant $O(N^2)$ prefix recomputation.
- **Dynamic Privacy Masking**: Added `kryntis/security/privacy_masker.py` providing three privacy tiers: Zero-Leak Data Processing (Enterprise financial/M&A/code masking), Double-Blind Research Safety (Scientific patient/trial masking), and Everyday Privacy Safeguard (Consumer PII/credit card sanitization).
- **Causal Counterfactual Simulation**: Added `kryntis/reasoning/counterfactual_simulator.py` supporting Risk & Market Modeling (Enterprise what-if supply chain stress-tests), Hypothesis Testing (Scientific in-silico simulation), and Empathetic Decision Support (Interpersonal boundary simulation).
- **Self-Falsifying Logic Engine**: Added `kryntis/reasoning/self_falsifying_logic.py` providing Flawless Compliance & Legal Audit (adversarial contract clause breaker), Academic Peer Review (anomaly and leap detector), and Anti-Hallucination Fact Guard.
- **Model Training Regression & Optimization Foundation**: Documented formal training objectives in `README.md` (Byte NLL cross-entropy loss, Cosine Annealing learning rate schedule, gradient norm clipping at $\tau=1.0$, and sigmoid-calibrated factual grounding regression).
- **Dataflow SVG Precise Border Alignment**: Resolved all connection lines and arrow endpoints in `assets/kryntis-dataflow.svg` so arrows connect directly to container and card boundaries.
- **Banner SVG Responsive Layout Fix**: Fixed `assets/kryntis-banner.svg` dimensions (1200x380 viewBox), eliminated badge/title text overlaps, and aligned responsive feature tags cleanly.
- **PyCharm & VSCode Run/Train Configurations**: Created launch and task configurations (`.vscode/launch.json`, `.vscode/tasks.json`) and PyCharm run configuration XMLs (`.idea/runConfigurations/*`) allowing 1-click training across all domains sequentially, individual domains, and interactive human feedback directly from the IDE UI.
- **Factual Grounding & Clarification Verifier**: Added `kryntis/orchestrator/grounding_verifier.py` to strictly evaluate information grounding, prevent hallucinations, and prompt the user for clarification whenever queries or data streams lack sufficient context.
- **Biomedical & Neural Telemetry Signal Analyzer**: Added `kryntis/tools/biometric_analyzer.py` with `TOOL_BIOMETRIC_ANALYZER` for processing structured sensor timeseries (EEG brainwaves, ECG cardiac rhythm, pulmonary respiration, thermal regulation) with strict factual calibration checks and user review prompts.
- **SOLID Persistence & Repository Pattern**: Created `kryntis/repositories/` module with generic interfaces (`IRepository`, `IDocumentRepository`, `ISessionRepository`, `IKnowledgeRepository`) and concrete implementations (`SQLiteDocumentRepository`, `SQLiteSessionRepository`, `InMemoryKnowledgeRepository`).
- **Dynamic Model Load Balancers**: Added `kryntis/core/load_balancer.py` implementing `RoundRobinLoadBalancer`, `WeightedLoadBalancer`, and `LeastLatencyLoadBalancer` for provider inference routing.
- **SOLID Multi-Tier Rate Limiters**: Refactored `kryntis/security/rate_limiter.py` into abstract `IRateLimiter`, `TokenBucketRateLimiter`, `SlidingWindowRateLimiter`, and `MultiTierRateLimiter`.
- **Multimodal Audio & Video Ingestion**: Added `kryntis/chunking/audio_chunker.py` and `kryntis/chunking/video_chunker.py` with strict 10 MB size limits and registered them in `kryntis/chunking/chunk_router.py`.
- **Guaranteed Universal Chunking**: Enforced that all ingestion flows route through `ChunkRouter`.
- **Voice System (TTS & STT)**: Added `kryntis/voice/tts_engine.py` (formant wave synthesizer + pyttsx3 fallback), `kryntis/voice/stt_engine.py` (signal acoustic analyzer + SpeechRecognition fallback), and `kryntis/voice/voice_interface.py` for conversational voice orchestration.
- **AI Tooling Ecosystem**: Created `kryntis/tools/tool_registry.py` and implemented 10 sandboxed tools (`code_interpreter`, `calculator`, `fs_read_file`, `fs_list_dir`, `web_fetch`, `sql_query`, `http_request`, `system_info`, `analyze_media`, and `biometric_telemetry_analyzer`).
- **5B Virtual Session Context Engine**: Created `kryntis/memory/session_context_manager.py` enabling up to 5,000,000,000 max context state per session using disk-backed SQLite storage. Integrated into `ShortTermMemory`.
- **User-Interactive Model Training**: Added `kryntis/learning/user_trainer.py` to collect user prompt-correction pairs and execute PyTorch fine-tuning gradient steps directly from user input.

### API & OpenAPI Specification
- **Interactive OpenAPI 3.1 & Swagger**: Configured enriched Swagger UI at `/docs`, ReDoc at `/redoc`, and comprehensive endpoint descriptions, tags, and response schemas in `kryntis/service/app.py`.
- **Voice Endpoints**: Added FastAPI router `kryntis/service/routers/voice.py` mounted at `/api/v1/voice` (`/synthesize`, `/transcribe`, `/chat`).
- **User Training Endpoints**: Added `POST /api/v1/admin/train/user-feedback` and `POST /api/v1/admin/train/user-run` in `kryntis/service/routers/admin.py`.
- **CLI Commands**: Added `generate-datasets`, `train-user-input`, and `train-interactive` commands to `main.py`.

### Data
- **Expanded Domain Catalog**: Added new pretraining domains to `kryntis/datasets/catalog.py`: `agi`, `fintech`, `military`, `government`, `media`, expanded universal polyglot coding (40+ languages), and healthcare.
- **Static Local JSONL Generation**: Updated `kryntis/datasets/synthetic_generator.py` and generated clean, self-contained JSONL corpora in `data/raw/` for all 14 domains.
- **Dataset Processor Updates**: Added 40+ language file extensions to `EXT_LANG_MAP` in `kryntis/datasets/processor.py` and processed domain corpora into `data/processed/`.

---

## Historical Versions

## v3.0.0

### Architecture
- **Byte-level encoding (v3):** Replaced BPE (v1) and natural-word (v2) tokenizers with a tokenizer-free byte processor (`kryntis/core/byte_processor.py`). Vocab size is now 260 (UTF-8 bytes + special tokens). `train_tokenizer` CLI command is a no-op.
- **Hybrid RAG:** Retrieval upgraded to BM25 (sparse) + dense vector search fused with Reciprocal Rank Fusion (RRF), followed by cross-encoder reranking.
- **Three-tier memory:** Short-term ring buffer, long-term vector memory, and episodic session storage added.
- **Internet research fallback:** Added `kryntis/internet/` pipeline.
- **Emotional intelligence layer:** `kryntis/core/emotional_intelligence.py` added.

---

## v2.0.0

### Architecture
- **Natural-word tokenizer (v2):** Added `kryntis/core/word_tokenizer.py`.
- **ChromaDB integration:** Replaced in-memory FAISS-only store with ChromaDB.
- **Document ingestion pipeline:** Added multi-format chunkers for PDF, DOCX, PPTX, XLSX, HTML, JSON, code, and images (OCR).

---

## v1.0.0

### Architecture
- Initial implementation: custom GPT-style decoder Transformer trained from scratch.
- BPE tokenizer (`kryntis/core/tokenizer.py`, `tokenizer_trainer.py`).
- Initial training domains: `english`, `regional_languages`, `emotion`, `coding`, `crm`, `sysadmin`.
