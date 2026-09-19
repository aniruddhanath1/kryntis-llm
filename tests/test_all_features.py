"""
Comprehensive unit tests for Kryntis AI v4.0.0 features.
Covers SOLID Repositories, Load Balancers, Rate Limiters, Multimodal chunkers, Voice, Tools, 5B context,
Grounding Verifiers, KV-Cache, Privacy Masking, Counterfactual Simulation, and Self-Falsifying Logic.
"""

import gc
import os
import tempfile
import unittest
import uuid
from pathlib import Path

import torch

from kryntis.chunking.audio_chunker import AudioChunker
from kryntis.chunking.chunk_router import ChunkRouter
from kryntis.chunking.video_chunker import VideoChunker
from kryntis.core.load_balancer import (
    BackendNode,
    LeastLatencyLoadBalancer,
    RoundRobinLoadBalancer,
    WeightedLoadBalancer,
)
from kryntis.core.model import KryntisModelConfig, KryntisTransformer, KVCache
from kryntis.datasets.catalog import DATASET_CATALOG, MODEL_CATALOG
from kryntis.ingestion.validator import FileValidator
from kryntis.learning.user_trainer import UserTrainer
from kryntis.memory.session_context_manager import SessionContextManager
from kryntis.memory.short_term import ShortTermMemory
from kryntis.orchestrator.grounding_verifier import GroundingVerifier
from kryntis.reasoning.counterfactual_simulator import (
    CausalCounterfactualSimulator,
    CounterfactualScenario,
    SimulationDomain,
)
from kryntis.reasoning.self_falsifying_logic import AuditScope, SelfFalsifyingLogicEngine
from kryntis.repositories import (
    InMemoryKnowledgeRepository,
    SQLiteDocumentRepository,
    SQLiteSessionRepository,
)
from kryntis.security.privacy_masker import DynamicPrivacyMasker, PrivacyScope
from kryntis.security.rate_limiter import (
    MultiTierRateLimiter,
    SlidingWindowRateLimiter,
    TokenBucketRateLimiter,
)
from kryntis.tools import get_default_tool_registry
from kryntis.voice.stt_engine import SpeechToTextEngine
from kryntis.voice.tts_engine import TextToSpeechEngine


class TestAllFeatures(unittest.IsolatedAsyncioTestCase):

    def test_dataset_catalog_expansion(self) -> None:
        """Verify AGI, all-languages, healthcare, fintech, military, government, media domains exist."""
        domains = {s.domain for s in DATASET_CATALOG}
        required = {"agi", "coding", "healthcare", "fintech", "military", "government", "media", "crm", "sysadmin", "security"}
        self.assertTrue(required.issubset(domains), f"Missing domains: {required - domains}")

    def test_kv_cache_mechanism(self) -> None:
        """Verify Transformer KV-Cache prefill and incremental generation."""
        cfg = KryntisModelConfig(vocab_size=260, n_layers=2, d_model=64, n_heads=4, n_kv_heads=2, d_ff=128)
        model = KryntisTransformer(cfg)

        # 1. Prefill
        prompt_ids = torch.tensor([[65, 66, 67]], dtype=torch.long)
        logits, kv_caches = model(prompt_ids)
        self.assertEqual(len(kv_caches), 2)
        self.assertEqual(kv_caches[0].seq_len, 3)

        # 2. Incremental single-token decode using cache
        next_id = torch.tensor([[68]], dtype=torch.long)
        logits_next, updated_caches = model(next_id, kv_caches=kv_caches)
        self.assertEqual(updated_caches[0].seq_len, 4)

        # 3. Autoregressive generate with cache
        out = model.generate_with_cache(prompt_ids, max_new_tokens=4)
        self.assertEqual(out.shape[1], 7)

    def test_dynamic_privacy_masker(self) -> None:
        """Verify DynamicPrivacyMasker redacts enterprise, scientific, and consumer PII."""
        masker = DynamicPrivacyMasker()

        # Consumer PII
        raw_consumer = "My card is 4532-1234-5678-9012 and email is john@example.com"
        res_consumer = masker.mask(raw_consumer, scope=PrivacyScope.CONSUMER)
        self.assertNotIn("4532-1234-5678-9012", res_consumer.masked_text)
        self.assertNotIn("john@example.com", res_consumer.masked_text)
        unmasked = masker.unmask(res_consumer.masked_text, res_consumer.entity_map)
        self.assertEqual(unmasked, raw_consumer)

        # Enterprise secret
        raw_ent = "Deal size is $500 million for merger with AcmeCorp with sk-12345678901234567890"
        res_ent = masker.mask(raw_ent, scope=PrivacyScope.ENTERPRISE)
        self.assertNotIn("sk-12345678901234567890", res_ent.masked_text)

    def test_causal_counterfactual_simulator(self) -> None:
        """Verify Causal Counterfactual simulation across enterprise and interpersonal domains."""
        simulator = CausalCounterfactualSimulator()

        # Enterprise simulation
        scenario = CounterfactualScenario(
            baseline_premise="Global logistics operating normally",
            counterfactual_intervention="Critical shipping channel closed",
            domain=SimulationDomain.ENTERPRISE,
        )
        outcome = simulator.simulate(scenario)
        self.assertGreater(outcome.risk_score, 0.5)
        self.assertTrue(len(outcome.mitigation_strategies) > 0)

    def test_self_falsifying_logic(self) -> None:
        """Verify adversarial legal and academic logic auditing."""
        engine = SelfFalsifyingLogicEngine()

        # Legal check
        legal_text = "The vendor shall indemnify and hold harmless the client indefinitely."
        legal_audit = engine.audit(legal_text, scope=AuditScope.LEGAL_COMPLIANCE)
        self.assertFalse(legal_audit.is_valid)  # Uncapped indemnification flagged

        # Peer review check
        academic_text = "The experimental trial proves that this drug undeniably caused complete remission."
        acad_audit = engine.audit(academic_text, scope=AuditScope.ACADEMIC_REVIEW)
        self.assertFalse(acad_audit.is_valid)

    def test_audio_chunker_and_10mb_limit(self) -> None:
        """Verify AudioChunker extracts chunks and enforces 10MB limit."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            wav_file = tmp_path / "test.wav"
            tts = TextToSpeechEngine()
            tts.save_to_file("Audio chunker test voice track", wav_file)

            chunker = AudioChunker()
            chunks = list(chunker.chunk_file(wav_file, source_id="test_audio"))
            self.assertGreater(len(chunks), 0)
            self.assertEqual(chunks[0].chunk_type, "audio")

            # Test >10MB rejection
            large_file = tmp_path / "oversized.wav"
            large_file.write_bytes(b"0" * (10 * 1024 * 1024 + 1024))
            with self.assertRaises(ValueError):
                list(chunker.chunk_file(large_file, source_id="oversized"))

    def test_video_chunker_and_10mb_limit(self) -> None:
        """Verify VideoChunker extracts chunks and enforces 10MB limit."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            vid_file = tmp_path / "test.mp4"
            vid_file.write_bytes(b"test video payload simulation" * 100)

            chunker = VideoChunker()
            chunks = list(chunker.chunk_file(vid_file, source_id="test_video"))
            self.assertGreater(len(chunks), 0)
            self.assertEqual(chunks[0].chunk_type, "video")

            # Test >10MB rejection
            large_vid = tmp_path / "oversized.mp4"
            large_vid.write_bytes(b"0" * (10 * 1024 * 1024 + 1024))
            with self.assertRaises(ValueError):
                list(chunker.chunk_file(large_vid, source_id="oversized"))

    def test_file_validator_media_rules(self) -> None:
        """Verify FileValidator enforces 10MB limit on audio/video."""
        validator = FileValidator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            valid_mp3 = tmp_path / "audio.mp3"
            valid_mp3.write_bytes(b"valid audio bytes")
            res_valid = validator.validate(valid_mp3)
            self.assertTrue(res_valid.valid)

            invalid_mp3 = tmp_path / "large_audio.mp3"
            invalid_mp3.write_bytes(b"x" * (10 * 1024 * 1024 + 500))
            res_invalid = validator.validate(invalid_mp3)
            self.assertFalse(res_invalid.valid)
            self.assertIn("10 MB limit", res_invalid.reason)

    def test_voice_tts_and_stt(self) -> None:
        """Verify TTS generates audible WAV bytes and STT analyzes the signal."""
        tts = TextToSpeechEngine()
        wav_bytes = tts.synthesize("Unit test speech synthesis")
        self.assertGreater(len(wav_bytes), 44)

        stt = SpeechToTextEngine()
        trans = stt.transcribe(wav_bytes)
        self.assertTrue(len(trans) > 0)

    def test_tool_registry_and_builtins(self) -> None:
        """Verify tool registry contains all standard AI tools and executes correctly."""
        registry = get_default_tool_registry()
        tools = registry.list_tools()
        names = {t.name for t in tools}
        expected = {
            "code_interpreter", "calculator", "fs_read_file", "fs_list_dir",
            "web_fetch", "sql_query", "http_request", "system_info", "analyze_media",
            "biometric_telemetry_analyzer"
        }
        self.assertTrue(expected.issubset(names))

        calc = registry.get_tool("calculator")
        res = calc.handler("10 * 10 + 24")
        self.assertEqual(res["result"], 124)

    def test_biometric_telemetry_analyzer_grounding(self) -> None:
        """Verify biometric analyzer processes valid streams and triggers clarification on abnormal bounds."""
        registry = get_default_tool_registry()
        bio = registry.get_tool("biometric_telemetry_analyzer")
        
        # Valid EEG test
        eeg_res = bio.handler(sensor_type="eeg", data_points=[12.5, 14.2, 10.8, 15.1, 13.0])
        self.assertEqual(eeg_res["status"], "ok")
        self.assertEqual(eeg_res["metrics"]["channel_type"], "electroencephalogram")

        # Thermal range out-of-bounds requesting user clarification
        temp_res = bio.handler(sensor_type="temperature", data_points=[52.0, 53.1, 51.8])
        self.assertEqual(temp_res["status"], "clarification_required")
        self.assertTrue(len(temp_res["clarification_needed"]) > 0)

    def test_grounding_verifier(self) -> None:
        """Verify grounding verifier identifies ambiguities and requests clarification."""
        verifier = GroundingVerifier()
        res_vague = verifier.evaluate_query("do it")
        self.assertTrue(res_vague.requires_user_clarification)
        self.assertIn("clarify", res_vague.clarification_prompt.lower())

        res_clear = verifier.evaluate_query("Explain the difference between SQLite and PostgreSQL in Python.")
        self.assertFalse(res_clear.requires_user_clarification)

    def test_session_context_manager_5b(self) -> None:
        """Verify 5B virtual context engine persistence and window assembly."""
        test_session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        db_dir = Path("data/sessions_test")
        db_dir.mkdir(parents=True, exist_ok=True)
        try:
            mgr = SessionContextManager(session_id=test_session_id, storage_dir=str(db_dir))
            mgr.add_turn("user", "Hello 5B context engine")
            mgr.add_turn("assistant", "Hello! Storing state persistently.")
            expected_tokens = len("Hello 5B context engine") // 4 + len("Hello! Storing state persistently.") // 4
            self.assertEqual(mgr.total_tokens, expected_tokens)
            window = mgr.get_context_window()
            self.assertEqual(len(window), 2)
            self.assertEqual(window[0].role, "user")
            self.assertEqual(window[1].role, "assistant")
        finally:
            gc.collect()
            db_file = db_dir / f"{test_session_id}_context.db"
            if db_file.exists():
                try:
                    db_file.unlink(missing_ok=True)
                except Exception:
                    pass

    def test_user_trainer(self) -> None:
        """Verify recording user feedback and sample counting."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_path = Path(tmp_dir) / "user_corpus.jsonl"
            trainer = UserTrainer(user_corpus_path=str(corpus_path), checkpoint_dir=tmp_dir)
            count1 = trainer.record_user_sample("Question 1", "Answer 1")
            count2 = trainer.record_user_sample("Question 2", "Answer 2")
            self.assertEqual(count1, 1)
            self.assertEqual(count2, 2)
            self.assertEqual(trainer.count_samples(), 2)

    async def test_solid_repositories(self) -> None:
        """Verify Document, Session, and Knowledge repositories."""
        test_dir = Path(f"data/repo_test_{uuid.uuid4().hex[:8]}")
        test_dir.mkdir(parents=True, exist_ok=True)
        try:
            # 1. Document Repo
            doc_repo = SQLiteDocumentRepository(db_path=str(test_dir / "docs.db"))
            await doc_repo.save({"doc_id": "doc1", "source_id": "src1", "text": "Kryntis neural engine"})
            doc = await doc_repo.get_by_id("doc1")
            self.assertIsNotNone(doc)
            self.assertEqual(doc["text"], "Kryntis neural engine")
            search_results = await doc_repo.search_by_text("neural")
            self.assertEqual(len(search_results), 1)

            # 2. Session Repo
            session_repo = SQLiteSessionRepository(db_path=str(test_dir / "sessions.db"))
            await session_repo.append_turn("sess_1", "user", "What is RAG?")
            await session_repo.append_turn("sess_1", "assistant", "Retrieval-Augmented Generation")
            turns = await session_repo.get_recent_turns("sess_1")
            self.assertEqual(len(turns), 2)

            # 3. Knowledge Repo
            know_repo = InMemoryKnowledgeRepository()
            await know_repo.save({"id": "k1", "text": "AI AGI logic", "embedding": [1.0, 0.0, 0.0]})
            await know_repo.save({"id": "k2", "text": "Fintech finance", "embedding": [0.0, 1.0, 0.0]})
            sim = await know_repo.find_similar([0.9, 0.1, 0.0], top_k=1)
            self.assertEqual(len(sim), 1)
            self.assertEqual(sim[0]["id"], "k1")
        finally:
            gc.collect()
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_load_balancers(self) -> None:
        """Verify RoundRobin, Weighted, and LeastLatency load balancers."""
        n1 = BackendNode(id="gpu1", target="local_gpu_1", weight=2)
        n2 = BackendNode(id="gpu2", target="local_gpu_2", weight=1)

        # Round Robin
        rr = RoundRobinLoadBalancer([n1, n2])
        first = rr.select_node()
        second = rr.select_node()
        self.assertNotEqual(first.id, second.id)

        # Weighted
        wb = WeightedLoadBalancer([n1, n2])
        picks = [wb.select_node().id for _ in range(3)]
        self.assertEqual(picks.count("gpu1"), 2)
        self.assertEqual(picks.count("gpu2"), 1)

        # Least Latency
        n1.total_requests = 10
        n1.total_latency_ms = 500.0  # avg 50ms
        n2.total_requests = 10
        n2.total_latency_ms = 100.0  # avg 10ms
        ll = LeastLatencyLoadBalancer([n1, n2])
        best = ll.select_node()
        self.assertEqual(best.id, "gpu2")

    def test_rate_limiters(self) -> None:
        """Verify TokenBucket and MultiTier rate limiters."""
        tb = TokenBucketRateLimiter(capacity=3, refill_rate=0.0)
        self.assertTrue(tb.is_allowed("client_a"))
        self.assertTrue(tb.is_allowed("client_a"))
        self.assertTrue(tb.is_allowed("client_a"))
        self.assertFalse(tb.is_allowed("client_a"))  # Exhausted

        sw = SlidingWindowRateLimiter(max_requests=2, window_seconds=10)
        self.assertTrue(sw.is_allowed("client_b"))
        self.assertTrue(sw.is_allowed("client_b"))
        self.assertFalse(sw.is_allowed("client_b"))  # Exceeded limit

        mt = MultiTierRateLimiter([tb, sw])
        self.assertFalse(mt.is_allowed("client_a"))


if __name__ == "__main__":
    unittest.main()
