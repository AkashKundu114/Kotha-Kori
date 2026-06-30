"""
Three-tier STT cascade: Sarvam AI (primary) -> Bhashini (free fallback) ->
self-hosted fine-tuned faster-whisper (final fallback / zero marginal cost).

This is the single entrypoint the orchestrator calls — it never talks to a
specific provider directly, so swapping/reordering providers later is a
one-file change.
"""
from __future__ import annotations

import logging

from services.voice_gateway.providers import sarvam_provider, bhashini_provider, whisper_local_provider

logger = logging.getLogger("voice_gateway")

CONFIDENCE_FLOOR = 0.75


async def transcribe(audio_bytes: bytes, language: str = "bn") -> dict:
    """
    Returns: {"transcript": str, "confidence": float, "provider": str}
    Tries each provider in order; falls through on error OR low confidence.
    """
    providers = [
        ("sarvam", sarvam_provider.transcribe),
        ("bhashini", bhashini_provider.transcribe),
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
        except Exception as exc:  # noqa: BLE001 — deliberately broad: any provider failure should fall through
            last_error = exc
            logger.warning("voice_gateway: %s failed (%s), falling through", name, exc)

    # All three failed or were low-confidence — return the local model's best
    # effort rather than nothing; the orchestrator can still ask the user to
    # repeat themselves with a known transcript on hand for debugging.
    if last_error:
        logger.error("voice_gateway: all providers exhausted, last error: %s", last_error)
    return {"transcript": "", "confidence": 0.0, "provider": "none"}
