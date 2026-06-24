from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import hmac, hashlib, json
from shared.config.settings import get_settings
from .router import route_message
from shared.whatsapp.parser import parse_webhook_payload

app = FastAPI(title="Kotha-Khata Gateway", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"])

@app.get("/health")
async def health(): return {"status": "ok"}

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
    if msg:
        background_tasks.add_task(route_message, msg)
    return {"status": "ok"}
