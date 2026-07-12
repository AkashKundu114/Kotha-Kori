from __future__ import annotations

import os
import tempfile

from faster_whisper import WhisperModel

from shared.config.settings import get_settings

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        s = get_settings()
        _model = WhisperModel(s.whisper_model_path, device=s.whisper_device, compute_type=s.whisper_compute_type)
    return _model


async def transcribe(audio_bytes: bytes, language: str = "bn") -> dict:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        wav_path = f.name

    try:
        model = _get_model()
        segments, info = model.transcribe(
            wav_path, language=language, beam_size=5, vad_filter=True, condition_on_previous_text=False
        )
        segments = list(segments)
        transcript = " ".join(seg.text.strip() for seg in segments)
        avg_logprob = sum(seg.avg_logprob for seg in segments) / max(len(segments), 1)
        confidence = min(1.0, max(0.0, avg_logprob + 1.0))
    finally:
        os.unlink(wav_path)

    return {"transcript": transcript.strip(), "confidence": round(confidence, 3)}
