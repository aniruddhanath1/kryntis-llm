"""
Voice router — Text-to-Speech, Speech-to-Text, and voice conversation endpoints.
"""

from __future__ import annotations

import base64
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Response
from pydantic import BaseModel, Field

from kryntis.voice.tts_engine import TextToSpeechEngine
from kryntis.voice.stt_engine import SpeechToTextEngine
from kryntis.voice.voice_interface import VoiceAssistant

router = APIRouter(tags=["Voice"])

_tts = TextToSpeechEngine()
_stt = SpeechToTextEngine()
_assistant = VoiceAssistant(tts=_tts, stt=_stt)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to convert to speech")
    speed: float = Field(default=1.0, ge=0.2, le=3.0, description="Speech rate multiplier")


class VoiceChatRequest(BaseModel):
    text: str | None = Field(default=None, description="Direct text input if audio not uploaded")
    session_id: str = Field(default="voice-session", description="Session identifier")
    speed: float = Field(default=1.0, ge=0.2, le=3.0, description="Speech rate multiplier")
    enable_rag: bool = Field(default=True, description="Enable RAG retrieval")
    enable_internet: bool = Field(default=True, description="Enable internet search")


@router.post("/synthesize", summary="Synthesize text to WAV audio")
async def synthesize_speech(req: TTSRequest):
    """Convert text into downloadable audio/wav bytes."""
    try:
        audio_bytes = _tts.synthesize(req.text, speed=req.speed)
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=kryntis_speech.wav"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis error: {e}")


@router.post("/transcribe", summary="Transcribe uploaded audio file to text")
async def transcribe_audio(file: UploadFile = File(...)):
    """Convert uploaded audio file into text."""
    try:
        content = await file.read()
        transcript = _stt.transcribe(content)
        return {"filename": file.filename, "transcript": transcript}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio transcription error: {e}")


@router.post("/chat", summary="End-to-end voice conversation")
async def voice_chat(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    session_id: str = Form("voice-session"),
    speed: float = Form(1.0),
    enable_rag: bool = Form(True),
    enable_internet: bool = Form(True),
):
    """
    Accepts an audio file or text, conducts conversational AI turn,
    and returns transcript, assistant response text, and base64-encoded WAV audio.
    """
    try:
        audio_data = None
        if file is not None:
            audio_data = await file.read()

        if not audio_data and not text:
            raise HTTPException(status_code=400, detail="Must provide either audio file or text.")

        result = await _assistant.interact(
            audio_input=audio_data,
            text_input=text,
            session_id=session_id,
            voice_speed=speed,
            enable_rag=enable_rag,
            enable_internet=enable_internet,
        )

        return {
            "session_id": result.session_id,
            "transcript": result.transcript,
            "response": result.response_text,
            "citations": result.citations,
            "audio_base64": result.audio_base64,
            "audio_format": "audio/wav",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice chat error: {e}")
