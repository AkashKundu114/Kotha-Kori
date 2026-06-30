from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import hmac, hashlib, json

from shared.config.settings import get_settings
from shared.whatsapp.parser import parse_webhook_payload
from services.orchestrator.celery_entrypoint import process_turn
from services.voice_gateway.provider_cascade import transcribe
from shared.whatsapp.media import download_whatsapp_audio

app = FastAPI(title="Kotha-Khata Gateway", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/webhook/whatsapp")
async def verify_webhook(request: Request):
    s = get_settings()
    p = request.query_params
    if p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == s.wa_webhook_verify_token:
        return Response(content=p.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook/whatsapp")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    s = get_settings()
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(s.wa_webhook_verify_token.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=403)

    payload = json.loads(body)
    msg = parse_webhook_payload(payload)
    if not msg:
        return {"status": "ok"}  # status update, not a message — nothing to do

    background_tasks.add_task(_dispatch_to_orchestrator, msg)
    return {"status": "ok"}


async def _dispatch_to_orchestrator(msg):
    """
    Build the turn_input dict and hand off to the LangGraph orchestrator via
    Celery. v1 had this logic spread across router.py's keyword if/elif
    chain; here it's just "figure out the input type, transcribe if needed,
    queue the graph" — the graph itself owns all routing decisions now.
    """
    turn_input: dict = {"last_message_type": msg.message_type}

    if msg.message_type == "text":
        turn_input["raw_input_text"] = msg.text
    elif msg.message_type == "audio":
        audio_bytes = await download_whatsapp_audio(msg.audio_id)
        stt_result = await transcribe(audio_bytes)
        turn_input["raw_input_transcript"] = stt_result["transcript"]
        turn_input["transcript_provider"] = stt_result["provider"]
        turn_input["transcript_confidence"] = stt_result["confidence"]
    elif msg.message_type == "interactive":
        # WhatsApp Flow completion payload (e.g. scheme_eligibility_flow.json)
        # — structured data, no STT/LLM extraction needed at all.
        turn_input["raw_input_text"] = json.dumps(msg.interactive_payload or {})
    # image handling (catalog/agri) follows the same pattern via a
    # dedicated vision node — left as a TODO; see docs/ARCHITECTURE.md.

    process_turn.delay(msg.from_number, turn_input)
