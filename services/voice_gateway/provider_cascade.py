from __future__ import annotations

import logging

from services.voice_gateway.providers import saaras_provider, whisper_local_provider

logger = logging.getLogger("voice_gateway")

CONFIDENCE_FLOOR = 0.60


async def transcribe(audio_bytes: bytes, language: str = "bn") -> dict:
    """Two-tier STT cascade, no OpenAI involved:
    1. Saaras V3 (Sarvam) — primary, paid, Bengali-native.
    2. Self-hosted faster-whisper (CPU) — free, zero-key fallback for uptime
       when Sarvam is briefly unavailable or rate-limited.
    Never raises — an exhausted cascade returns an empty transcript so the
    caller can show a friendly 'didn't catch that, try again' message
    instead of crashing."""
    providers = [
        ("saaras-v3", saaras_provider.transcribe),
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
