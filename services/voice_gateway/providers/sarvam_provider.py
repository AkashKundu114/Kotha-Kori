import base64
import httpx

from shared.config.settings import get_settings

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

async def transcribe(audio_bytes: bytes, language: str = "bn") -> dict:
    s = get_settings()
    if not s.sarvam_api_key:
        raise RuntimeError("SARVAM_API_KEY not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            SARVAM_STT_URL,
            headers={"api-subscription-key": s.sarvam_api_key},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"language_code": f"{language}-IN", "model": "saarika:v2"},
        )
        r.raise_for_status()
        body = r.json()

    return {
        "transcript": body.get("transcript", "").strip(),

        "confidence": body.get("confidence", 0.92),
    }

async def synthesize(text_bengali: str, voice: str = "meera") -> bytes:

    s = get_settings()
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(
            SARVAM_TTS_URL,
            headers={"api-subscription-key": s.sarvam_api_key},
            json={"inputs": [text_bengali], "target_language_code": "bn-IN", "speaker": voice},
        )
        r.raise_for_status()
        audio_b64 = r.json()["audios"][0]
    return base64.b64decode(audio_b64)
