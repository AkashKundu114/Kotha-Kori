from __future__ import annotations

import io

from openai import AsyncOpenAI

from shared.config.settings import get_settings


async def transcribe(audio_bytes: bytes, language: str = "bn") -> dict:
    s = get_settings()
    if not s.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    client = AsyncOpenAI(api_key=s.openai_api_key, timeout=20.0, max_retries=1)
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.ogg"  # SDK reads this to set the multipart filename

    resp = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language=language,
    )
    text = (resp.text or "").strip()
    # whisper-1 doesn't return a confidence score; treat a non-empty
    # transcript from a strong hosted model as high-confidence.
    return {"transcript": text, "confidence": 0.90 if text else 0.0}
