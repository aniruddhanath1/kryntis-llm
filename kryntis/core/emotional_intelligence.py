"""
Emotional Intelligence Module — Emotional state modeling, tone detection, and empathetic response shaping.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class EmotionState(str, Enum):
    NEUTRAL = "neutral"
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    EMPATHY = "empathy"
    FRUSTRATION = "frustration"
    CURIOSITY = "curiosity"


@dataclass
class EmotionalProfile:
    primary_emotion: EmotionState
    confidence: float
    valence: float       # -1.0 (Negative) to +1.0 (Positive)
    arousal: float       # 0.0 (Calm) to 1.0 (Excited/Intense)
    empathy_required: bool = False


# Keyword & Pattern Heuristics for Fast In-Process Emotional Intelligence
_EMOTION_PATTERNS = {
    EmotionState.JOY: [r"\b(happy|great|awesome|love|thanks|thank you|excellent|excited|wonderful|cool)\b"],
    EmotionState.SADNESS: [r"\b(sad|depressed|unhappy|disappointed|sorry|hopeless|heartbroken|grief)\b"],
    EmotionState.ANGER: [r"\b(angry|mad|furious|annoyed|hate|stupid|terrible|horrible|useless|rage)\b"],
    EmotionState.FEAR: [r"\b(scared|afraid|worried|anxious|panic|frightened|nervous|terrified)\b"],
    EmotionState.FRUSTRATION: [r"\b(frustrated|stuck|not working|failed|broken|why|confused|help)\b"],
    EmotionState.CURIOSITY: [r"\b(how|why|what|curious|wonder|explain|tell me|explore)\b"],
}


class EmotionalIntelligenceEngine:
    """
    Analyzes input text to detect emotional tone, sentiment valence, and empathy requirements,
    and formats emotional prompt modifiers for the AI response.
    """

    def analyze(self, text: str) -> EmotionalProfile:
        lower_text = text.lower()
        
        detected_emotions: dict[EmotionState, float] = {}
        for emotion, patterns in _EMOTION_PATTERNS.items():
            matches = 0
            for pat in patterns:
                matches += len(re.findall(pat, lower_text))
            if matches > 0:
                detected_emotions[emotion] = matches

        if not detected_emotions:
            return EmotionalProfile(
                primary_emotion=EmotionState.NEUTRAL,
                confidence=0.9,
                valence=0.0,
                arousal=0.1,
                empathy_required=False,
            )

        # Primary emotion is the one with highest match score
        primary = max(detected_emotions.items(), key=lambda x: x[1])[0]
        
        # Calculate valence & empathy requirement
        empathy_required = False
        valence = 0.0
        arousal = 0.5

        if primary in (EmotionState.SADNESS, EmotionState.ANGER, EmotionState.FRUSTRATION, EmotionState.FEAR):
            valence = -0.7
            empathy_required = True
            arousal = 0.7 if primary in (EmotionState.ANGER, EmotionState.FRUSTRATION) else 0.4
        elif primary == EmotionState.JOY:
            valence = 0.8
            arousal = 0.6
        elif primary == EmotionState.CURIOSITY:
            valence = 0.3
            arousal = 0.4

        log.debug("emotional_analysis", primary=primary.value, empathy=empathy_required)
        return EmotionalProfile(
            primary_emotion=primary,
            confidence=0.85,
            valence=valence,
            arousal=arousal,
            empathy_required=empathy_required,
        )

    def get_system_prompt_modifier(self, profile: EmotionalProfile) -> str:
        """Generates system prompt directives to guide response emotional tone."""
        if profile.empathy_required:
            return (
                f"\n\n[Emotional Intelligence Directive]: The user is feeling {profile.primary_emotion.value}. "
                "Respond with deep empathy, active listening, patience, and supportive encouragement. "
                "Acknowledge their state before diving into technical solutions."
            )
        elif profile.primary_emotion == EmotionState.JOY:
            return (
                f"\n\n[Emotional Intelligence Directive]: The user is in a joyful, positive state. "
                "Maintain a warm, enthusiastic, and collaborative tone."
            )
        elif profile.primary_emotion == EmotionState.CURIOSITY:
            return (
                f"\n\n[Emotional Intelligence Directive]: The user is curious. "
                "Provide clear, engaging, and insightful explanations."
            )
        return ""
