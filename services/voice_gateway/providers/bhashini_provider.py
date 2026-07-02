
import base64
import httpx

from shared.config.settings import get_settings

BHASHINI_PIPELINE_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

async def transcribe(audio_bytes: bytes, language: str = "bn") -> dict:
    s = get_settings()
    if not s.bhashini_api_key:
        raise RuntimeError("BHASHINI_API_KEY not configured")

    audio_b64 = base64.b64encode(audio_bytes).decode()
    payload = {
        "pipelineTasks": [
            {
                "taskType": "asr",
                "config": {
                    "language": {"sourceLanguage": language},
                    "serviceId": "ai4bharat/conformer-bn-gpu--t4",
                    "audioFormat": "wav",
                    "samplingRate": 16000,
                },
            }
        ],
        "inputData": {"audio": [{"audioContent": audio_b64}]},
    }

    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.post(
            BHASHINI_PIPELINE_URL,
            headers={
                "userID": s.bhashini_user_id,
                "ulcaApiKey": s.bhashini_api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        r.raise_for_status()
        result = r.json()

    transcript = result["pipelineResponse"][0]["output"][0]["source"]

    return {"transcript": transcript.strip(), "confidence": 0.78}
