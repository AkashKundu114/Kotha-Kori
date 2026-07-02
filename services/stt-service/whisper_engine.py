
from faster_whisper import WhisperModel
from shared.config.settings import get_settings
import subprocess, tempfile, os

_model: WhisperModel | None = None

def get_model() -> WhisperModel:
    global _model
    if _model is None:
        s = get_settings()
        _model = WhisperModel(
            s.whisper_model_path,
            device=s.whisper_device,
            compute_type=s.whisper_compute_type,
        )
    return _model

def ogg_to_wav(ogg_bytes: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(ogg_bytes); ogg = f.name
    wav = ogg.replace(".ogg", ".wav")
    subprocess.run(
        ["ffmpeg", "-i", ogg, "-ar", "16000", "-ac", "1", wav, "-y", "-loglevel", "error"],
        check=True
    )
    with open(wav, "rb") as f: data = f.read()
    os.unlink(ogg); os.unlink(wav)
    return data

def transcribe(audio_bytes: bytes) -> dict:

    wav_bytes = ogg_to_wav(audio_bytes)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes); wav_path = f.name

    model = get_model()
    segments, info = model.transcribe(
        wav_path,
        language="bn",
        beam_size=5,
        word_timestamps=True,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500}
    )

    transcript = " ".join(seg.text.strip() for seg in segments)
    avg_logprob = sum(seg.avg_logprob for seg in segments) / max(len(list(segments)), 1)
    confidence = min(1.0, max(0.0, (avg_logprob + 1.0)))

    os.unlink(wav_path)
    return {
        "transcript": transcript.strip(),
        "confidence": round(confidence, 3),
        "language": info.language,
        "provider": "whisper-finetuned"
    }
