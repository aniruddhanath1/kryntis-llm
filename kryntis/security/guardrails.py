"""
Guardrail pipeline — unified input and output policy enforcement.

Two guard classes run as ordered rule chains:

  InputGuardrails  — runs before the prompt reaches the LLM:
    1. Length enforcement
    2. Prompt injection / instruction-override detection
    3. Toxic / harmful-request detection
    4. PII scrubbing (redact rather than block)

  OutputGuardrails — runs on the LLM response before returning to caller:
    1. Harmful content blocking
    2. PII redaction
    3. Low-confidence / uncertainty flagging

GuardrailPipeline wires both together, reading thresholds from KryntisConfig.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from kryntis.utils.logging import get_logger

log = get_logger(__name__)


# ── Result types ──────────────────────────────────────────────────────────────

class GuardrailAction(str, Enum):
    ALLOW  = "allow"
    BLOCK  = "block"
    REDACT = "redact"   # text was modified and sanitised
    WARN   = "warn"     # allowed but flagged in metadata


@dataclass
class GuardrailResult:
    action: GuardrailAction
    text: str                               # original or sanitised text
    rule: str = ""                          # id of the rule that fired
    reason: str = ""                        # human-readable explanation
    metadata: dict = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        return self.action == GuardrailAction.BLOCK

    @property
    def passed(self) -> bool:
        return self.action in (GuardrailAction.ALLOW, GuardrailAction.REDACT, GuardrailAction.WARN)


# ── Rule tables ───────────────────────────────────────────────────────────────

_INJECTION_RULES: list[tuple[str, str]] = [
    (r"ignore (previous|all|prior|above) instructions",     "prompt_injection"),
    (r"you are now\b",                                      "persona_override"),
    (r"forget (everything|all previous)",                   "context_wipe"),
    (r"act as (if you are|a|an)\b",                         "persona_override"),
    (r"do anything now\b",                                  "jailbreak_dan"),
    (r"\bjailbreak\b",                                      "jailbreak"),
    (r"disregard (your|all) (training|instructions)",       "instruction_override"),
    (r"reveal (your|the) (system|hidden) prompt",           "system_prompt_leak"),
    (r"print (your|the) (system|initial) (message|prompt)", "system_prompt_leak"),
    (r"write malware|create a (virus|trojan|worm)",         "malware_request"),
    (r"exploit (this|the) (system|server|api)",             "exploit_request"),
    (r"<\|.*?\|>",                                          "token_injection"),
    (r"\[\[.*?\]\]",                                        "template_injection"),
    (r"<!--.*?-->",                                         "html_comment_injection"),
    (r"(?:```|<%|{%)[\s\S]{0,200}(?:system|admin|root)",   "code_block_injection"),
]

_TOXIC_RULES: list[tuple[str, str]] = [
    (r"\b(ddos|denial.of.service attack|botnet control)\b",                 "cyberattack_request"),
    (r"\b(child (pornography|sexual abuse|exploitation))\b",                "csam"),
    (r"\bhow to (make|build|create|synthesize) (bomb|explosive|fentanyl|meth|nerve.?agent)\b",
                                                                            "dangerous_synthesis"),
    (r"\b(generate|write|create).{0,30}(ransomware|rootkit|keylogger)\b",   "malware_generation"),
]

_PII_INPUT_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),               "[EMAIL]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),          "[PHONE]"),
    (re.compile(r"\b4[0-9]{12}(?:[0-9]{3})?\b"),                                        "[CARD]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                                              "[SSN]"),
    (re.compile(r"(?:password|passwd|secret|token|api[-_]?key)\s*[:=]\s*\S+",
                re.IGNORECASE),                                                          "[CREDENTIAL]"),
]

_PII_OUTPUT_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),               "[EMAIL]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),          "[PHONE]"),
    (re.compile(r"\b4[0-9]{12}(?:[0-9]{3})?\b"),                                        "[CARD]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                                              "[SSN]"),
    (re.compile(r"(?:sk|pk|api)[-_][a-zA-Z0-9]{20,}",          re.IGNORECASE),         "[API_KEY]"),
    (re.compile(r"(?:password|passwd|secret)\s*[:=]\s*\S+",     re.IGNORECASE),         "[CREDENTIAL]"),
    (re.compile(r"\b[A-Z0-9]{32,}\b"),                                                  "[TOKEN]"),
]

_HARMFUL_OUTPUT_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(step \d[.\)].{0,120}\b(bomb|explosive|synthesis)\b)",
                re.IGNORECASE | re.DOTALL),  "harmful_synthesis_steps"),
    (re.compile(r"\b(here is|below is).{0,40}(malware|exploit code|rootkit|payload)",
                re.IGNORECASE),              "malware_output"),
]

_UNCERTAINTY_PHRASES = frozenset([
    "i'm not sure", "i am not sure", "i don't know", "i do not know",
    "i cannot confirm", "i may be wrong", "i'm uncertain", "i am uncertain",
    "as an ai", "i lack the ability to verify",
])

# Pre-compile injection + toxic patterns once
_COMPILED_INJECTION = [(re.compile(p, re.IGNORECASE | re.DOTALL), r) for p, r in _INJECTION_RULES]
_COMPILED_TOXIC     = [(re.compile(p, re.IGNORECASE), r) for p, r in _TOXIC_RULES]


# ── Input guardrails ──────────────────────────────────────────────────────────

class InputGuardrails:
    """
    Ordered chain: length → injection → toxic → PII scrub.

    On BLOCK the original text is preserved in the result (not sent to LLM).
    On REDACT the sanitised text is in result.text (send this to LLM instead).
    """

    def __init__(
        self,
        max_length: int = 8192,
        block_injection: bool = True,
        block_toxic: bool = True,
        strip_pii: bool = False,
    ) -> None:
        self._max_length = max_length
        self._block_injection = block_injection
        self._block_toxic = block_toxic
        self._strip_pii = strip_pii

    def run(self, text: str, session_id: str = "") -> GuardrailResult:
        ctx = {"session_id": session_id}

        # ── 1. Length ─────────────────────────────────────────────────────
        if len(text) > self._max_length:
            log.warning("guardrail_input_length", length=len(text), **ctx)
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                text=text,
                rule="max_length",
                reason=f"Input exceeds {self._max_length:,} characters.",
            )

        # ── 2. Prompt injection ───────────────────────────────────────────
        if self._block_injection:
            for pattern, rule in _COMPILED_INJECTION:
                if pattern.search(text):
                    log.warning("guardrail_injection", rule=rule, **ctx)
                    return GuardrailResult(
                        action=GuardrailAction.BLOCK,
                        text=text,
                        rule=rule,
                        reason="Potential prompt injection or instruction override detected.",
                    )

        # ── 3. Toxic / harmful ────────────────────────────────────────────
        if self._block_toxic:
            for pattern, rule in _COMPILED_TOXIC:
                if pattern.search(text):
                    log.warning("guardrail_toxic", rule=rule, **ctx)
                    return GuardrailResult(
                        action=GuardrailAction.BLOCK,
                        text=text,
                        rule=rule,
                        reason="Request contains prohibited content.",
                    )

        # ── 4. PII scrubbing (redact, not block) ──────────────────────────
        if self._strip_pii:
            original = text
            for pattern, replacement in _PII_INPUT_RULES:
                text = pattern.sub(replacement, text)
            if text != original:
                log.info("guardrail_input_pii_redacted", **ctx)
                return GuardrailResult(
                    action=GuardrailAction.REDACT,
                    text=text,
                    rule="pii_scrub",
                    reason="PII detected and redacted from input.",
                )

        return GuardrailResult(action=GuardrailAction.ALLOW, text=text, rule="pass")


# ── Output guardrails ─────────────────────────────────────────────────────────

class OutputGuardrails:
    """
    Ordered chain: harmful block → PII redaction → uncertainty flag.

    Blocking replaces the response with a safe fallback string.
    Redaction modifies result.text in place.
    Uncertainty is surfaced in result.metadata (never blocks).
    """

    def __init__(
        self,
        block_harmful: bool = True,
        redact_pii: bool = True,
        flag_uncertainty: bool = True,
        min_confidence: float = 0.0,
    ) -> None:
        self._block_harmful = block_harmful
        self._redact_pii = redact_pii
        self._flag_uncertainty = flag_uncertainty
        self._min_confidence = min_confidence

    def run(self, text: str, confidence: float = 1.0, session_id: str = "") -> GuardrailResult:
        ctx = {"session_id": session_id}

        # ── 1. Block harmful output ───────────────────────────────────────
        if self._block_harmful:
            for pattern, rule in _HARMFUL_OUTPUT_RULES:
                if pattern.search(text):
                    log.error("guardrail_output_harmful", rule=rule, **ctx)
                    return GuardrailResult(
                        action=GuardrailAction.BLOCK,
                        text="I'm unable to provide that information.",
                        rule=rule,
                        reason="Response contained prohibited content and was blocked.",
                    )

        # ── 2. PII redaction ──────────────────────────────────────────────
        if self._redact_pii:
            original = text
            for pattern, replacement in _PII_OUTPUT_RULES:
                text = pattern.sub(replacement, text)
            if text != original:
                log.info("guardrail_output_pii_redacted", **ctx)

        # ── 3. Confidence / uncertainty flagging ──────────────────────────
        metadata: dict = {}
        if self._flag_uncertainty:
            if confidence < self._min_confidence:
                metadata["low_confidence"] = True
                metadata["confidence"] = round(confidence, 4)
            lower = text.lower()
            if any(phrase in lower for phrase in _UNCERTAINTY_PHRASES):
                metadata["uncertainty_detected"] = True

        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            text=text,
            rule="pass",
            metadata=metadata,
        )


# ── Composite pipeline ────────────────────────────────────────────────────────

class GuardrailPipeline:
    """
    Single entry point for all guardrail checks.

    Instantiate once and reuse (cheap; all regex is pre-compiled at module level).

    Example:
        pipeline = GuardrailPipeline()

        result = pipeline.check_input(user_text, session_id=sid)
        if result.blocked:
            return {"error": result.reason}

        response_text = llm.generate(result.text)   # result.text may be redacted

        result = pipeline.check_output(response_text, confidence=0.9, session_id=sid)
        return {"response": result.text, "flags": result.metadata}
    """

    def __init__(self) -> None:
        from kryntis.utils.config import get_config
        cfg = get_config()
        sec = cfg.security
        self.input = InputGuardrails(
            max_length=sec.max_prompt_length,
            block_injection=sec.prompt_injection_detection,
            block_toxic=sec.block_toxic_input,
            strip_pii=sec.strip_pii_from_input,
        )
        self.output = OutputGuardrails(
            block_harmful=sec.block_harmful_output,
            redact_pii=sec.redact_pii_from_output,
            flag_uncertainty=sec.flag_uncertain_output,
            min_confidence=cfg.evaluation.min_confidence_to_respond,
        )

    def check_input(self, text: str, session_id: str = "") -> GuardrailResult:
        return self.input.run(text, session_id=session_id)

    def check_output(
        self, text: str, confidence: float = 1.0, session_id: str = ""
    ) -> GuardrailResult:
        return self.output.run(text, confidence=confidence, session_id=session_id)


# Module-level singleton
_pipeline: GuardrailPipeline | None = None


def get_guardrail_pipeline() -> GuardrailPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = GuardrailPipeline()
    return _pipeline
