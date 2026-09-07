# Kryntis AI — Implementation Plan (v1 & v2 History)

## Revision History

- **v1.0 (2026-08-13)**: Initial architecture using GGUF base models & BPE tokenization.
- **v3.0 (2026-08-21)**: Tokenizer-Free Byte / ASCII Direct Architecture (`ByteDirectProcessor`). Maps characters and words directly to UTF-8 / ASCII byte integers (0–255) and 8-bit binary representations, eliminating all subword and word tokenizers.

---

# Version 3.0 (Current Version) — Tokenizer-Free Byte / ASCII Direct Architecture

## Key v3.0 Architecture Innovations

1. **Tokenizer-Free Direct Byte Processing (`kryntis/core/byte_processor.py`)**:
   - Completely eliminates subword dictionaries, vocabulary building, and subword splitting algorithms.
   - Text is read and processed directly as **raw ASCII / UTF-8 byte values (0–255)** and **8-bit binary matrices**.
   - Language model vocabulary is fixed to 256 bytes + 4 special control symbols (`VOCAB_SIZE = 260`), matching low-level machine execution and assembly/binary level comprehension.

2. **Sequential Pretraining in Tokenizer-Free Mode**:
   - **Task 1 (English Natural Language & Grammar)**:
     ```bash
     python main.py download-datasets --domain english
     python main.py process-datasets --domain english
     python main.py train --domain english
     ```
   - **Task 2 (World Regional Languages)**:
     ```bash
     python main.py download-datasets --domain regional_languages
     python main.py process-datasets --domain regional_languages
     python main.py train --domain regional_languages --resume
     ```

3. **Task 3: PostgreSQL + pgvector VectorDB Integration**:
   - Integrated [`kryntis/knowledge/pgvector_adapter.py`](file:///e:/Personal/Kryntis%20AI/kryntis-llm/kryntis/knowledge/pgvector_adapter.py) for PostgreSQL vector databases.

---

## Key v2.2 Training & System Tasks

### Task 1: English Natural Language & Grammar Pretraining
- **Goal**: Download English Grammar, train on it sequentially, and master natural English sentences, words, and characters.
- **Datasets**: `salesforce/wikitext`, `allenai/c4`.
- **Engine**: Natural English Word-Level Tokenizer (`NaturalEnglishTokenizer`).
- **Commands**:
  ```bash
  python main.py download-datasets --domain english
  python main.py process-datasets --domain english
  python main.py train-tokenizer --natural
  python main.py train --domain english
  ```

### Task 2: World Regional Human-Speaking Languages Pretraining
- **Goal**: Download and train on world regional natural human-speaking languages.
- **Datasets**: `allenai/c4` (mC4 Multilingual). Completely public & unauthenticated (no Hugging Face API key or authentication needed).
- **Commands**:
  ```bash
  python main.py download-datasets --domain regional_languages
  python main.py process-datasets --domain regional_languages
  python main.py train --domain regional_languages --resume
  ```

### Task 3: PostgreSQL + pgvector VectorDB Integration
- **Goal**: VectorDB adapter (`PGVectorAdapter`) for storing embeddings and document datasets directly in a PostgreSQL instance using `pgvector`.
- **Implementation**: [`kryntis/knowledge/pgvector_adapter.py`](file:///e:/Personal/Kryntis%20AI/kryntis-llm/kryntis/knowledge/pgvector_adapter.py).
- **Configuration**: Set `vector_backend = "postgres"` or `KRYNTIS_VECTOR_BACKEND=postgres`.

---

## Key v2.1 Architecture Innovations

1. **Domain-Sequential One-by-One Pretraining**:
   - Training is modularized into discrete domains (`english`, `emotion`, `coding`, `security`, `healthcare`).
   - Prevents memory spikes and allows granular, step-by-step training per domain.
   - Command flags: `python main.py download-datasets --domain english`, `python main.py process-datasets --domain english`, `python main.py train --domain english`.

2. **Multi-Segment Intelligence Expansion**:
   - **Coding**: Software engineering, multi-language coding, patterns (Python, Java, C#, Apex, ABAP, Dynamics 365).
   - **Security & Device Patching**: Vulnerability assessment, patch analysis, device hardware security QA (`sec-qa`).
   - **Healthcare**: Clinical medical QA & medical knowledge corpus (`med-qa`).
   - **Emotional Intelligence (EQ)**: Conversational emotion grounding & empathy (`dair-ai/emotion`).
   - **Natural English**: Grammar, syntax & structure (`wikitext-103`, `c4`).

3. **Autonomous Reasoning & RAG Real-Time Result Verification**:
   - Hybrid dense/sparse retrieval with RRF rank fusion guarantees facts are sourced in real-time, eliminating hallucinations.
   - Continual Learning pipeline allows the AI brain to dynamically adapt and absorb new knowledge over time.

---

1. **No External API Dependencies**: 100% self-contained Python ML engine running locally.
2. **Natural Word-Level Tokenizer (`kryntis/core/word_tokenizer.py`)**: Replaced BPE subword splitting with natural English word/lexical tokenization so the model processes language directly as whole human words and punctuation.
3. **Emotional Intelligence Engine (`kryntis/core/emotional_intelligence.py`)**:
   - Detects user sentiment, emotional state (Joy, Sadness, Anger, Fear, Frustration, Curiosity), valence, and arousal.
   - Dynamically injects empathetic directives into the Orchestrator prompt pipeline.
4. **Natural English & Grammar Datasets**:
   - Integrated `WikiText-103`, `C4-English`, and `Empathetic Dialogues` datasets alongside programming datasets.
5. **Phase 1 & Phase 2 Multi-Language Pretraining**:
   - Phase 1: Natural English, Python, Java, C#, JavaScript, Go.
   - Phase 2: Salesforce Apex, SAP ABAP, Dynamics 365, PHP, Ruby, Perl.
6. **Strict Resource-Aware Guard (`kryntis/utils/task_queue.py`)**:
   - Maximum 1 heavy process (training, dataset download, processing) at a time.
   - Pre-flight RAM safety check: pauses/rejects jobs if available RAM < 1000 MB.
   - Bounded worker count (defaults to 1 worker on <= 8 GB RAM machines).
   - Streaming/chunk-based processing with explicit `gc.collect()` garbage collection after heavy stages.

---

## v2 System Architecture Diagram

```
[React Frontend] ──HTTP──▶ [Java Spring Boot API]
                                    │
                                HTTP/REST
                                    │
                           ┌────────▼──────────────────────────┐
                           │  Kryntis AI Engine v2 (this repo) │
                           │  Internal FastAPI Service         │
                           │                                   │
                           │  Orchestrator + EQ Engine         │
                           │  ├─ Emotional Intelligence (EQ)   │
                           │  ├─ Intent Router                 │
                           │  └─ ReAct Agent Loop              │
                           │                                   │
                           │  Core LLM                         │
                           │  ├─ Natural Word Tokenizer        │
                           │  ├─ Decoder Transformer (Scratch) │
                           │  └─ Local PyTorch Provider        │
                           │                                   │
                           │  Datasets & Learning              │
                           │  ├─ English Grammar (Wiki/C4)     │
                           │  ├─ Empathetic Dialogues          │
                           │  └─ Code (HF + GitHub)            │
                           └───────────────────────────────────┘
```

---

## Build Commands (v2)

```bash
# 1. Download English Grammar + Emotional + Coding Datasets
python main.py download-datasets --phase 1

# 2. Process Datasets into Clean JSONL Corpus
python main.py process-datasets

# 3. Train Natural Word-Level Tokenizer
python main.py train-tokenizer

# 4. Train Model from Scratch
python main.py train

# 5. Serve Local FastAPI Server
python main.py serve
```

---

# Version 1.0 (Historical Architecture)

## Project Scope (v1)

| Layer | This Repo | Later |
|-------|-----------|-------|
| AI Engine (LLM, RAG, Memory, Chunking, Learning…) | ✅ Built here | — |
| Internal AI Service (thin FastAPI, called by Java) | ✅ Built here | — |
| Business APIs | — | Java Spring Boot |
| User-facing Frontend | — | React |
| Auth / User management | — | Java Spring Boot |

---

## v1 Architecture Diagram

```
[React Frontend] ──HTTP──▶ [Java Spring Boot API]
                                    │
                                HTTP/REST
                                    │
                           ┌────────▼──────────────────────────┐
                           │  Kryntis AI Engine  (this repo)    │
                           │  Internal FastAPI Service           │
                           │                                    │
                           │  Orchestrator                      │
                           │  ├─ Intent Router                  │
                           │  ├─ Task Planner                   │
                           │  └─ Agent Loop (ReAct)             │
                           │                                    │
                           │  LLM Core                         │
                           │  ├─ Tokenizer (scratch BPE)        │
                           │  ├─ Transformer model              │
                           │  ├─ Inference Engine               │
                           │  └─ Model Manager (load/unload)    │
                           │                                    │
                           │  RAG Engine                       │
                           │  ├─ Embedder                      │
                           │  ├─ Retriever (dense + sparse)     │
                           │  └─ Reranker                      │
                           │                                    │
                           │  Memory                           │
                           │  ├─ Short-term (conv buffer)       │
                           │  ├─ Long-term (semantic vector)    │
                           │  └─ Episodic                      │
                           │                                    │
                           │  Chunking Engine                  │
                           │  ├─ PDF, DOCX, PPTX               │
                           │  ├─ XLSX, CSV, JSON, HTML         │
                           │  └─ Code, TXT, Images             │
                           │                                    │
                           │  Internet Research Pipeline        │
                           │  └─ Search→Fetch→Validate→Cite    │
                           │                                    │
                           │  Knowledge Store                  │
                           │  ├─ ChromaDB (vector)             │
                           │  └─ SQLite (metadata/provenance)  │
                           │                                    │
                           │  Continual Learning               │
                           │  Security · Evaluation            │
                           └───────────────────────────────────┘
```

---

## v1 Technology Stack

| Component | Library |
|-----------|---------|
| Core ML | PyTorch |
| Base Model | TinyLlama-1.1B-Q4 via `llama-cpp-python` |
| Custom Tokenizer | Pure Python BPE + tiktoken |
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2) |
| Vector DB | ChromaDB (disk-persistent) |
| Relational DB | SQLite via `aiosqlite` |
| Internal API | FastAPI + uvicorn |

---

*Last updated: 2026-08-13 (Version 2.0)*
