from __future__ import annotations

import httpx

from shared.config.settings import get_settings


async def transcribe(audio_bytes: bytes, language: str = "bn") -> dict:
    """Saaras V3 (Sarvam's STT model) — replaces the old OpenAI Whisper API
    tier. Same call shape as sarvam_provider's transcribe for consistency."""
    s = get_settings()
    if not s.sarvam_api_key:
        raise RuntimeError("SARVAM_API_KEY not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            f"{s.sarvam_base_url}/speech-to-text",
            headers={"api-subscription-key": s.sarvam_api_key},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"language_code": f"{language}-IN", "model": s.saaras_model},
        )
        r.raise_for_status()
        body = r.json()

    return {
        "transcript": body.get("transcript", "").strip(),
        "confidence": body.get("confidence", 0.92),
    }
