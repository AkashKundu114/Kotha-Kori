from __future__ import annotations

import logging

from services.voice_gateway.providers import openai_stt_provider, whisper_local_provider

logger = logging.getLogger("voice_gateway")

CONFIDENCE_FLOOR = 0.60


async def transcribe(audio_bytes: bytes, language: str = "bn") -> dict:
    """Two-tier STT cascade, both usable with just an OpenAI key:
    1. OpenAI Whisper API (whisper-1) — primary, no separate account needed.
    2. Self-hosted faster-whisper (CPU) — free, zero-key fallback for uptime
       when OpenAI is briefly unavailable or rate-limited.
    Never raises — an exhausted cascade returns an empty transcript so the
    caller can show a friendly 'didn't catch that, try again' message
    instead of crashing."""
    providers = [
        ("openai-whisper", openai_stt_provider.transcribe),
        ("whisper-local", whisper_local_provider.transcribe),
    ]

    last_error: Exception | None = None
    for name, fn in providers:
        try:
            result = await fn(audio_bytes, language=language)
            if result["confidence"] >= CONFIDENCE_FLOOR:
                result["provider"] = name
                return result
            logger.warning("voice_gateway: %s low confidence (%.2f), falling through", name, result["confidence"])
        except Exception as exc:
            last_error = exc
            logger.warning("voice_gateway: %s failed (%s), falling through", name, exc)

    if last_error:
        logger.error("voice_gateway: all providers exhausted, last error: %s", last_error)
    return {"transcript": "", "confidence": 0.0, "provider": "none"}
