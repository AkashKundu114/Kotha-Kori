from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import hmac, hashlib, json, time, uuid

import redis.asyncio as aioredis

from shared.config.settings import get_settings
from shared.storage.s3_client import get_s3_client
from shared.whatsapp.parser import parse_webhook_payload
from services.orchestrator.celery_entrypoint import process_turn
from services.voice_gateway.provider_cascade import transcribe
from shared.whatsapp.media import (
    download_whatsapp_audio,
    download_whatsapp_image,
    MediaTooLargeError,
)

app = FastAPI(title="Kotha-Khata Gateway", version="3.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"])

_redis: aioredis.Redis | None = None
MAX_IMAGE_BYTES = 5 * 1024 * 1024
DEDUP_TTL_SECONDS = 86400


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        s = get_settings()
        _redis = aioredis.from_url(s.redis_url, decode_responses=True)
    return _redis


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/webhook/whatsapp")
async def verify_webhook(request: Request):
    s = get_settings()
    p = request.query_params
    if (
        p.get("hub.mode") == "subscribe"
        and p.get("hub.verify_token") == s.wa_webhook_verify_token
    ):
        return Response(content=p.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook/whatsapp")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    s = get_settings()
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")

    expected = (
        "sha256=" + hmac.new(s.wa_app_secret.encode(), body, hashlib.sha256).hexdigest()
    )
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=403)

    payload = json.loads(body)
    msg = parse_webhook_payload(payload)
    if not msg:
        return {"status": "ok"}

    redis = await get_redis()

    was_new = await redis.set(
        f"dedup:{msg.message_id}", "1", ex=DEDUP_TTL_SECONDS, nx=True
    )
    if not was_new:
        return {"status": "ok"}

    rate_key = f"ratelimit:{msg.from_number}:{int(time.time() // 3600)}"
    count = await redis.incr(rate_key)
    await redis.expire(rate_key, 3600)
    if count > s.max_messages_per_hour:
        return {"status": "ok"}

    background_tasks.add_task(_dispatch_to_orchestrator, msg)
    return {"status": "ok"}


async def _dispatch_to_orchestrator(msg):
    s = get_settings()
    turn_input: dict = {"last_message_type": msg.message_type}

    try:
        if msg.message_type == "text":
            turn_input["raw_input_text"] = msg.text

        elif msg.message_type == "audio":
            audio_bytes = await download_whatsapp_audio(msg.audio_id)
            stt_result = await transcribe(audio_bytes)
            turn_input["raw_input_transcript"] = stt_result["transcript"]
            turn_input["transcript_provider"] = stt_result["provider"]
            turn_input["transcript_confidence"] = stt_result["confidence"]

        elif msg.message_type == "image":
            image_bytes = await download_whatsapp_image(msg.image_id)
            s3 = get_s3_client()
            key = f"catalog-raw/{msg.from_number}/{uuid.uuid4().hex[:10]}.jpg"
            s3.put_object(
                Bucket=s.s3_bucket,
                Key=key,
                Body=image_bytes,
                ServerSideEncryption="AES256",
            )
            turn_input["raw_image_s3_key"] = key

        elif msg.message_type == "interactive":
            turn_input["raw_input_text"] = json.dumps(msg.interactive_payload or {})

        else:
            return

        process_turn.delay(msg.from_number, turn_input)

    except MediaTooLargeError:
        from shared.whatsapp.sender import send_text

        friendly = (
            "ভয়েস নোটটা অনেক বড়। ৩ মিনিটের কম রেকর্ড করে আবার পাঠান।"
            if msg.message_type == "audio"
            else "ছবিটা অনেক বড়। একটু ছোট সাইজে পাঠান।"
        )
        await send_text(msg.from_number, friendly)

    except Exception:
        from shared.whatsapp.sender import send_text

        await send_text(msg.from_number, "দুঃখিত, একটু সমস্যা হয়েছে। আবার চেষ্টা করুন।")
        raise
