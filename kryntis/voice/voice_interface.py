"""
Voice Assistant Interface — conversational end-to-end audio pipeline.

Transcribes incoming voice, processes through the central AI orchestrator,
and synthesizes the response back to audio.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path

from kryntis.orchestrator.agent_loop import AIOrchestrator, OrchestratorRequest
from kryntis.voice.stt_engine import SpeechToTextEngine
from kryntis.voice.tts_engine import TextToSpeechEngine
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class VoiceInteractionResult:
    """Result of a voice conversation turn."""
    transcript: str
    response_text: str
    audio_wav_bytes: bytes
    session_id: str
    citations: list[dict] = field(default_factory=list)
    audio_base64: str = ""

    def __post_init__(self):
        if not self.audio_base64 and self.audio_wav_bytes:
            self.audio_base64 = base64.b64encode(self.audio_wav_bytes).decode("utf-8")


class VoiceAssistant:
    """
    End-to-end voice assistant coordinator.
    """

    def __init__(
        self,
        orchestrator: AIOrchestrator | None = None,
        tts: TextToSpeechEngine | None = None,
        stt: SpeechToTextEngine | None = None,
    ) -> None:
        self.orchestrator = orchestrator or AIOrchestrator()
        self.tts = tts or TextToSpeechEngine()
        self.stt = stt or SpeechToTextEngine()

    async def interact(
        self,
        audio_input: bytes | Path | None = None,
        text_input: str | None = None,
        session_id: str = "voice-session",
        voice_speed: float = 1.0,
        enable_rag: bool = True,
        enable_internet: bool = True,
    ) -> VoiceInteractionResult:
        """
        Execute an end-to-end conversational turn via voice.

        Args:
            audio_input: Spoken audio data (bytes or path).
            text_input: Optional text input if already transcribed.
            session_id: Session identifier.
            voice_speed: Speed for speech synthesis.
            enable_rag: Whether RAG retrieval is enabled.
            enable_internet: Whether internet search is enabled.

        Returns:
            VoiceInteractionResult containing transcript, text, audio bytes, and base64.
        """
        # 1. Transcribe audio if provided
        if audio_input is not None:
            transcript = self.stt.transcribe(audio_input)
        elif text_input:
            transcript = text_input
        else:
            raise ValueError("Either audio_input or text_input must be provided.")

        log.info("voice_interaction_start", session_id=session_id, transcript=transcript)

        # 2. Orchestrate AI response
        req = OrchestratorRequest(
            session_id=session_id,
            user_message=transcript,
            enable_rag=enable_rag,
            enable_internet=enable_internet,
            stream=False,
        )
        resp = await self.orchestrator.chat(req)

        # 3. Synthesize speech audio response
        audio_bytes = self.tts.synthesize(resp.response, speed=voice_speed)

        return VoiceInteractionResult(
            transcript=transcript,
            response_text=resp.response,
            audio_wav_bytes=audio_bytes,
            session_id=session_id,
            citations=resp.citations,
        )
