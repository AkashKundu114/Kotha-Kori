# Kotha-Kori (কথা-কড়ি)
## Implementation Plan
**Version:** 1.0 | **Scope:** Phase 0 + Phase 1 (Weeks 1–18, MVP) | **Date:** June 2026

---

## 1. Team Structure

| Role | Count | Responsibilities |
|------|-------|-----------------|
| **Backend Engineer (Lead)** | 1 | FastAPI services, DB schema, Celery workers, WhatsApp API |
| **Backend Engineer** | 1 | RAG pipeline, Entity extraction service, PDF generation |
| **ML Engineer** | 1 | STT integration, EfficientNet training, Bhashini/Whisper pipelines |
| **Full-Stack Engineer** | 1 | NGO dashboard (Phase 2), Bengali UI components |
| **DevOps Engineer** | 0.5 | Kubernetes, CI/CD, monitoring, Terraform |
| **Product Manager** | 1 | Requirements, user testing, NGO liaison, content (Bengali copy) |

> For a 2-person founding team, collapse to: 1 full-stack engineer (takes Backend + Full-Stack roles) + 1 ML engineer (takes ML + partial DevOps). Use managed services (Supabase, Upstash, Railway) to minimize DevOps burden in MVP.

---

## 2. Environment Setup (Week 1)

### 2.1 Repository Structure
```
kotha-khata/
├── services/
│   ├── gateway/              # FastAPI webhook receiver
│   ├── ai-worker/            # Celery AI processing tasks
│   ├── stt-service/          # Bhashini + Whisper STT
│   ├── rag-service/          # Scheme RAG engine
│   ├── vision-service/       # Image processing
│   ├── pdf-service/          # Report generation
│   └── notification-service/ # Proactive alerts
├── shared/
│   ├── db/                   # SQLAlchemy models, Alembic migrations
│   ├── redis/                # Session management utilities
│   ├── whatsapp/             # WhatsApp API client
│   └── config/               # Environment config, secrets
├── ml/
│   ├── whisper-finetune/     # Whisper fine-tuning scripts
│   ├── efficientnet-agri/    # Crop disease model training
│   └── ner-bengali/          # spaCy NER training
├── data/
│   ├── schemes/              # Scheme PDFs and scraped content
│   ├── training-audio/       # STT evaluation test set
│   └── crop-diseases/        # Agricultural training images
├── dashboard/                # NGO React dashboard (Phase 2)
├── infrastructure/
│   ├── terraform/            # IaC for AWS
│   ├── k8s/                  # Kubernetes manifests
│   └── docker/               # Dockerfiles
├── scripts/
│   ├── seed_schemes.py       # Initial scheme data ingestion
│   ├── eval_stt.py           # STT accuracy evaluation
│   └── audit_rag.py          # RAG hallucination audit
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/             # Bengali audio samples, test images
```

### 2.2 Development Tools Setup Checklist
- [ ] GitHub repository + branch protection rules (main, staging, dev)
- [ ] GitHub Actions workflows: lint, test, build, deploy
- [ ] Docker Desktop + Docker Compose (local dev)
- [ ] AWS account setup + IAM roles (least privilege)
- [ ] Supabase project (PostgreSQL + pgvector extension enabled)
- [ ] Upstash Redis (serverless, generous free tier for MVP)
- [ ] AWS S3 bucket (PDF + image storage)
- [ ] Meta Business Account → WhatsApp Business API access request (start immediately — 2–4 week process)
- [ ] Bhashini ULCA API registration (apply Week 1)
- [ ] Anthropic API key (Claude claude-sonnet-4-6)
- [ ] OpenAI API key (embeddings + GPT-4o for vision)
- [ ] Sentry project for error tracking
- [ ] ngrok for local webhook testing (WhatsApp webhook requires HTTPS)

---

## 3. Phase 0: Foundation (Weeks 1–6)

### Week 1: Project Skeleton + WhatsApp Webhook

**Day 1–2: Core Setup**
```python
# Task: Create FastAPI app with webhook endpoint

# services/gateway/main.py
from fastapi import FastAPI, Request, BackgroundTasks
import hmac, hashlib

app = FastAPI()

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    # 1. Verify Meta signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403)
    
    # 2. Acknowledge immediately (Meta requires < 20s)
    payload = await request.json()
    background_tasks.add_task(process_message, payload)
    return {"status": "ok"}

@app.get("/webhook/whatsapp")
async def verify_webhook(request: Request):
    # Meta webhook verification handshake
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge)
    raise HTTPException(status_code=403)
```

**Day 3–4: Message Extraction Utilities**
```python
# shared/whatsapp/parser.py
from dataclasses import dataclass
from typing import Optional, Literal

@dataclass
class IncomingMessage:
    message_id: str
    from_number: str  # E.164 format
    timestamp: int
    message_type: Literal["text", "audio", "image", "document"]
    text: Optional[str] = None
    audio_id: Optional[str] = None  # Meta media ID
    image_id: Optional[str] = None
    audio_mime_type: Optional[str] = None

def parse_webhook_payload(payload: dict) -> Optional[IncomingMessage]:
    """Extract message from Meta's webhook payload"""
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]["value"]
        if "messages" not in change:
            return None  # status update, not a message
        
        msg = change["messages"][0]
        base = IncomingMessage(
            message_id=msg["id"],
            from_number=msg["from"],
            timestamp=int(msg["timestamp"]),
            message_type=msg["type"]
        )
        
        if msg["type"] == "text":
            base.text = msg["text"]["body"]
        elif msg["type"] == "audio":
            base.audio_id = msg["audio"]["id"]
            base.audio_mime_type = msg["audio"]["mime_type"]
        elif msg["type"] == "image":
            base.image_id = msg["image"]["id"]
        
        return base
    except (KeyError, IndexError):
        return None
```

**Day 5: WhatsApp Message Sender**
```python
# shared/whatsapp/sender.py
import httpx

WHATSAPP_API_URL = "https://graph.facebook.com/v18.0/{phone_number_id}/messages"

async def send_text(to: str, body: str, phone_number_id: str, token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            WHATSAPP_API_URL.format(phone_number_id=phone_number_id),
            headers={"Authorization": f"Bearer {token}"},
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"body": body, "preview_url": False}
            }
        )
        return response.json()

async def send_document(to: str, document_url: str, filename: str, caption: str, ...):
    # Similar structure with type="document"
    pass

async def send_image(to: str, image_url: str, caption: str, ...):
    # Similar structure with type="image"
    pass
```

**Exit Criteria Week 1:** Send a WhatsApp message to the bot; receive "Kotha-Khata te swagat! আপনার কোথা-খাতায় স্বাগতম!" back within 5 seconds.

---

### Week 2: Redis Sessions + Onboarding Flow

```python
# shared/redis/session.py
import json
import redis.asyncio as aioredis
from enum import Enum

class ConversationState(str, Enum):
    IDLE = "IDLE"
    ONBOARDING_NAME = "ONBOARDING_NAME"
    ONBOARDING_SHG = "ONBOARDING_SHG"
    ONBOARDING_DISTRICT = "ONBOARDING_DISTRICT"
    LEDGER_AWAIT_INPUT = "LEDGER_AWAIT_INPUT"
    LEDGER_CONFIRM = "LEDGER_CONFIRM"
    SCHEME_IDENTIFY = "SCHEME_IDENTIFY"
    # ... etc

SESSION_TTL = 1800  # 30 minutes

async def get_session(redis: aioredis.Redis, number: str) -> dict:
    data = await redis.get(f"session:{number}")
    if data:
        return json.loads(data)
    return {"state": ConversationState.IDLE, "context": {}}

async def set_session(redis: aioredis.Redis, number: str, session: dict):
    await redis.setex(
        f"session:{number}", 
        SESSION_TTL,
        json.dumps(session, default=str)
    )
```

**Onboarding Dialogue (Bengali):**
```
User: শুরু  (or SHURU or Hi)

Bot: কোথা-খাতায় আপনাকে স্বাগতম! 🙏
     আমি আপনার ব্যবসার হিসাব রাখতে, সরকারি প্রকল্প জানাতে, 
     আর আপনার পণ্যের বিজ্ঞাপন বানাতে সাহায্য করব।
     
     শুরু করতে, আপনার নাম বলুন।

User: সুনীতা দাস

Bot: সুনীতা দি, আপনার স্বনির্ভর গোষ্ঠীর নাম কী?

User: মা দুর্গা গোষ্ঠী

Bot: খুব ভালো! আপনি কোন জেলায় থাকেন?
     (মুর্শিদাবাদ / দক্ষিণ ২৪ পরগনা / বীরভূম / পুরুলিয়া / 
      কোচবিহার / অন্য জেলা)

User: মুর্শিদাবাদ

Bot: ধন্যবাদ সুনীতা দি! ✅
     আপনার কোথা-খাতা তৈরি হয়ে গেছে।
     
     এখন থেকে আপনি পারবেন:
     🎙️ বিক্রি/খরচ ভয়েসে বলুন
     📋 সরকারি প্রকল্প জানুন  
     📸 পণ্যের ছবি পাঠান
     📊 মাসের হিসাব নিন
     
     আজকের বিক্রি বা খরচ বলতে চান?
```

---

### Week 3: Database Schema + Alembic Migrations

```python
# shared/db/models.py (SQLAlchemy 2.0)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, ARRAY, String, Numeric, Boolean, Text
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    whatsapp_number: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    shg_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shg_groups.id"))
    district: Mapped[str | None] = mapped_column(String(100))
    block: Mapped[str | None] = mapped_column(String(100))
    pin_code: Mapped[str | None] = mapped_column(String(6))
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarded_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_active_at: Mapped[datetime | None]
    is_group_leader: Mapped[bool] = mapped_column(Boolean, default=False)

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    entry_date: Mapped[datetime]
    entry_type: Mapped[str] = mapped_column(String(10))  # INCOME | EXPENSE
    amount_inr: Mapped[float] = mapped_column(Numeric(10, 2))
    category: Mapped[str | None] = mapped_column(String(100))
    description_bengali: Mapped[str | None] = mapped_column(Text)
    raw_transcript: Mapped[str | None] = mapped_column(Text)
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

class SchemeChunk(Base):
    __tablename__ = "scheme_chunks"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scheme_documents.id"))
    chunk_text: Mapped[str] = mapped_column(Text)
    chunk_bengali: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))
    chunk_index: Mapped[int]
```

**Migration command:**
```bash
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

---

### Week 4: Bhashini STT Integration

```python
# services/stt-service/bhashini.py
import httpx
import base64
import asyncio
from pathlib import Path

BHASHINI_PIPELINE_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

async def download_whatsapp_audio(media_id: str, token: str) -> bytes:
    """Download audio file from Meta's media servers"""
    async with httpx.AsyncClient() as client:
        # Step 1: Get download URL
        url_response = await client.get(
            f"https://graph.facebook.com/v18.0/{media_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        download_url = url_response.json()["url"]
        
        # Step 2: Download audio
        audio_response = await client.get(
            download_url,
            headers={"Authorization": f"Bearer {token}"}
        )
        return audio_response.content

async def convert_ogg_to_wav(ogg_bytes: bytes) -> bytes:
    """Convert OGG/OPUS to WAV 16kHz mono using ffmpeg"""
    import subprocess, tempfile, os
    
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(ogg_bytes)
        ogg_path = f.name
    
    wav_path = ogg_path.replace(".ogg", ".wav")
    subprocess.run([
        "ffmpeg", "-i", ogg_path, 
        "-ar", "16000", "-ac", "1", "-f", "wav",
        wav_path, "-y", "-loglevel", "error"
    ], check=True)
    
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()
    
    os.unlink(ogg_path)
    os.unlink(wav_path)
    return wav_bytes

async def transcribe_bengali(audio_bytes: bytes) -> dict:
    """Transcribe Bengali audio using Bhashini ASR"""
    audio_b64 = base64.b64encode(audio_bytes).decode()
    
    payload = {
        "pipelineTasks": [{
            "taskType": "asr",
            "config": {
                "language": {"sourceLanguage": "bn"},
                "serviceId": "ai4bharat/conformer-bn-gpu--t4",
                "audioFormat": "wav",
                "samplingRate": 16000
            }
        }],
        "inputData": {
            "audio": [{"audioContent": audio_b64}]
        }
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            BHASHINI_PIPELINE_URL,
            headers={
                "userID": BHASHINI_USER_ID,
                "ulcaApiKey": BHASHINI_API_KEY,
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        result = response.json()
        transcript = result["pipelineResponse"][0]["output"][0]["source"]
        
        return {
            "transcript": transcript,
            "provider": "bhashini",
            "confidence": 0.90  # Bhashini doesn't return confidence; use heuristic
        }
```

---

### Week 5: Celery Task Queue

```python
# services/ai-worker/tasks.py
from celery import Celery
import asyncio

celery_app = Celery(
    "kotha_khata",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

celery_app.conf.task_routes = {
    "tasks.process_voice_ledger": {"queue": "ledger"},
    "tasks.process_scheme_query": {"queue": "rag"},
    "tasks.process_catalog_image": {"queue": "vision"},
    "tasks.generate_pdf_report": {"queue": "pdf"},
}

@celery_app.task(
    name="tasks.process_voice_ledger",
    max_retries=3,
    default_retry_delay=5
)
def process_voice_ledger(
    message_id: str,
    from_number: str,
    audio_id: str
):
    """
    Full pipeline: download audio → STT → NER → confirm → save
    """
    try:
        # 1. Download and convert audio
        audio_bytes = asyncio.run(download_whatsapp_audio(audio_id, WA_TOKEN))
        wav_bytes = asyncio.run(convert_ogg_to_wav(audio_bytes))
        
        # 2. Transcribe
        stt_result = asyncio.run(transcribe_bengali(wav_bytes))
        transcript = stt_result["transcript"]
        
        # 3. Extract financial entities
        entities = extract_financial_entities(transcript)
        
        # 4. Build confirmation message
        confirmation = build_ledger_confirmation(entities)
        
        # 5. Update session state to LEDGER_CONFIRM
        session = get_session(from_number)
        session["state"] = "LEDGER_CONFIRM"
        session["context"]["pending_entry"] = entities
        session["context"]["transcript"] = transcript
        set_session(from_number, session)
        
        # 6. Send confirmation to user
        asyncio.run(send_text(from_number, confirmation))
        
    except Exception as exc:
        # Send error message to user
        asyncio.run(send_text(
            from_number, 
            "দুঃখিত, একটু সমস্যা হলো। আবার চেষ্টা করুন।"
        ))
        raise process_voice_ledger.retry(exc=exc)
```

---

### Week 6: Entity Extraction (NER + LLM)

```python
# services/ai-worker/entity_extraction.py
import anthropic
import json
import re

client = anthropic.Anthropic()

LEDGER_EXTRACTION_PROMPT = """You are a Bengali financial entity extractor for rural SHG women's micro-businesses.

Extract financial transactions from this Bengali text. Return ONLY valid JSON, no explanation.

Bengali text: {transcript}

Return JSON with this exact structure:
{{
  "transactions": [
    {{
      "type": "INCOME" or "EXPENSE",
      "amount_inr": <number>,
      "item": "<product/service in English>",
      "item_bengali": "<product/service in Bengali>",
      "quantity": <number or null>,
      "unit": "<unit or null>",
      "confidence": <0.0-1.0>
    }}
  ],
  "date_hint": "<today/yesterday/date if mentioned, else null>",
  "overall_confidence": <0.0-1.0>
}}

Rules:
- Bengali number words: এক=1, দুই=2, তিন=3, চার=4, পাঁচ=5, দশ=10, পনেরো=15, বিশ=20, পঁচিশ=25, ত্রিশ=30, পঞ্চাশ=50, একশো=100, দুইশো=200, তিনশো=300, পাঁচশো=500, হাজার=1000
- Extract ALL transactions from the text, even if multiple
- If amount is ambiguous, set confidence < 0.7
"""

def extract_financial_entities(transcript: str) -> dict:
    """Use Claude to extract financial entities from Bengali transcript"""
    
    # First try: fast regex for simple patterns
    simple_result = try_regex_extraction(transcript)
    if simple_result and simple_result["overall_confidence"] > 0.85:
        return simple_result
    
    # Fallback: LLM extraction
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": LEDGER_EXTRACTION_PROMPT.format(transcript=transcript)
        }]
    )
    
    raw = message.content[0].text
    # Strip any markdown if present
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)

def try_regex_extraction(transcript: str) -> dict | None:
    """Fast path: simple Bengali transaction patterns"""
    # Pattern: "X taka Y bikri" or "Y bikri X taka"
    patterns = [
        r"(\d+)\s*(?:taka|টাকা)\s+(.+?)\s+(?:bikri|বিক্রি)",
        r"(.+?)\s+(?:bikri|বিক্রি)\s+(\d+)\s*(?:taka|টাকা)",
    ]
    # ... regex implementation
    return None  # Fall through to LLM if complex

def build_ledger_confirmation(entities: dict) -> str:
    """Build Bengali confirmation message from extracted entities"""
    lines = ["আমি এইটুকু বুঝলাম:"]
    
    total_income = 0
    total_expense = 0
    
    for tx in entities["transactions"]:
        if tx["type"] == "INCOME":
            total_income += tx["amount_inr"]
            qty_str = f"{tx['quantity']} {tx['unit']} " if tx.get("quantity") else ""
            lines.append(f"✅ আয়: {qty_str}{tx['item_bengali']} → ₹{tx['amount_inr']}")
        else:
            total_expense += tx["amount_inr"]
            lines.append(f"📤 খরচ: {tx['item_bengali']} → ₹{tx['amount_inr']}")
    
    net = total_income - total_expense
    lines.append(f"\n📊 মোট আয়: ₹{total_income}")
    lines.append(f"📊 মোট খরচ: ₹{total_expense}")
    lines.append(f"💰 লাভ: ₹{net}")
    lines.append("\nঠিক আছে? (হ্যাঁ/না)")
    
    return "\n".join(lines)
```

---

### Week 7–10: Full Ledger Flow + Correction Handling

**Correction Flow:**
```python
async def handle_ledger_correction(from_number: str, text: str, session: dict):
    """User says 'bhul hoyeche' or 'na' — handle correction"""
    
    pending = session["context"].get("pending_entry")
    transcript = session["context"].get("transcript", "")
    
    # Re-extract with correction context
    correction_prompt = f"""
    Original Bengali: {transcript}
    User correction: {text}
    
    Previous extraction: {json.dumps(pending)}
    
    Apply the user's correction and return the updated extraction JSON.
    """
    
    updated_entities = extract_with_correction(transcript, text, pending)
    session["context"]["pending_entry"] = updated_entities
    session["state"] = "LEDGER_CONFIRM"
    await set_session_async(from_number, session)
    
    confirmation = build_ledger_confirmation(updated_entities)
    await send_text(from_number, f"ঠিক আছে, আবার দেখুন:\n\n{confirmation}")
```

---

### Week 11–14: PDF Generation

```python
# services/pdf-service/generator.py
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
import boto3
from datetime import date

env = Environment(loader=FileSystemLoader("templates/"))

async def generate_monthly_report(user_id: str, year: int, month: int) -> str:
    """Generate monthly P&L PDF and return S3 URL"""
    
    # 1. Fetch data from DB
    entries = await fetch_ledger_entries(user_id, year, month)
    user = await fetch_user(user_id)
    shg = await fetch_shg(user.shg_id)
    
    # 2. Calculate summary
    income_by_category = {}
    expense_by_category = {}
    
    for entry in entries:
        if entry.entry_type == "INCOME":
            income_by_category.setdefault(entry.category, 0)
            income_by_category[entry.category] += entry.amount_inr
        else:
            expense_by_category.setdefault(entry.category, 0)
            expense_by_category[entry.category] += entry.amount_inr
    
    total_income = sum(income_by_category.values())
    total_expense = sum(expense_by_category.values())
    net_profit = total_income - total_expense
    
    # 3. Render HTML template
    template = env.get_template("monthly_report.html")
    html_content = template.render(
        member_name=user.name,
        shg_name=shg.name if shg else "",
        district=user.district,
        month_bengali=BENGALI_MONTHS[month],
        year=year,
        income_by_category=income_by_category,
        expense_by_category=expense_by_category,
        total_income=total_income,
        total_expense=total_expense,
        net_profit=net_profit,
        generated_date=date.today().strftime("%d/%m/%Y"),
        entries=entries
    )
    
    # 4. Convert to PDF
    pdf_bytes = HTML(string=html_content, base_url="templates/").write_pdf()
    
    # 5. Upload to S3
    s3_key = f"reports/{user_id}/{year}/{month}/report.pdf"
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket="kotha-khata-reports",
        Key=s3_key,
        Body=pdf_bytes,
        ContentType="application/pdf",
        ServerSideEncryption="AES256"
    )
    
    # Generate presigned URL (valid 24 hours)
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": "kotha-khata-reports", "Key": s3_key},
        ExpiresIn=86400
    )
    return url

BENGALI_MONTHS = {
    1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল",
    5: "মে", 6: "জুন", 7: "জুলাই", 8: "আগস্ট",
    9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর"
}
```

**PDF Bengali HTML Template (key section):**
```html
<!-- templates/monthly_report.html -->
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;700&display=swap');
    body { font-family: 'Noto Sans Bengali', sans-serif; }
    .header { background: #1a5276; color: white; padding: 20px; text-align: center; }
    .profit { color: #1e8449; font-size: 24px; font-weight: bold; }
    .disclaimer { font-size: 10px; color: #666; border-top: 1px solid #ccc; }
  </style>
</head>
<body>
  <div class="header">
    <h1>কোথা-খাতা | মাসিক আয়-ব্যয় বিবরণী</h1>
    <p>{{ member_name }} | {{ shg_name }} | {{ district }}</p>
    <p>{{ month_bengali }} {{ year }}</p>
  </div>
  <!-- Income table, Expense table, Summary, Disclaimer -->
  <div class="disclaimer">
    এই নথিটি স্বনির্ভর গোষ্ঠীর সদস্যের ব্যক্তিগত ব্যবসায়িক লেনদেনের ভিত্তিতে তৈরি।
    ব্যাংক ঋণের জন্য সহায়ক নথি হিসেবে ব্যবহার করা যেতে পারে।
    কোথা-খাতা কোনো আর্থিক পরামর্শ প্রদান করে না।
  </div>
</body>
</html>
```

---

### Week 15–18: Scheme RAG + Pilot Deployment

```python
# services/rag-service/pipeline.py
from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
import anthropic

Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

ANTI_HALLUCINATION_SYSTEM = """
তুমি পশ্চিমবঙ্গের স্বনির্ভর গোষ্ঠীর মহিলাদের জন্য একজন সরকারি প্রকল্প সহায়ক।

কঠোর নিয়ম:
1. শুধুমাত্র নিচে দেওয়া context থেকে উত্তর দাও।
2. Context-এ উত্তর না থাকলে বলো: "এ বিষয়ে নিশ্চিত তথ্য নেই। পঞ্চায়েত অফিসে জিজ্ঞেস করুন।"
3. টাকার পরিমাণ, যোগ্যতার শর্ত বা তারিখ কখনো অনুমান করো না।
4. সহজ, কথ্য বাংলায় উত্তর দাও।
5. প্রতিটি তথ্যের সাথে বলো কোন প্রকল্পের নথি থেকে নেওয়া।
"""

async def query_scheme_rag(
    query: str, 
    user_context: dict,
    scheme_filter: list[str] | None = None
) -> dict:
    """Query the scheme RAG system with hallucination prevention"""
    
    # 1. Embed query
    embedding = await embed_text(query)
    
    # 2. Hybrid retrieval
    semantic_results = await pgvector_search(embedding, top_k=10, scheme_filter=scheme_filter)
    keyword_results = await bm25_search(query, top_k=10, scheme_filter=scheme_filter)
    
    # 3. Reciprocal rank fusion
    merged = reciprocal_rank_fusion(semantic_results, keyword_results, top_k=5)
    
    if not merged:
        return {
            "answer_bengali": "এ বিষয়ে নিশ্চিত তথ্য নেই। পঞ্চায়েত অফিসে জিজ্ঞেস করুন।",
            "citations": [],
            "hallucination_check_passed": True
        }
    
    # 4. Build context from retrieved chunks
    context = "\n\n---\n\n".join([
        f"[{r['scheme_name']} - {r['document_type']}]\n{r['chunk_text']}"
        for r in merged
    ])
    
    # 5. Generate grounded response
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=ANTI_HALLUCINATION_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Context:\n{context}\n\nUser question: {query}\n\nUser details: {json.dumps(user_context)}"
        }]
    )
    
    answer = message.content[0].text
    
    # 6. Hallucination check: verify no claim lacks citation
    hallucination_check = verify_grounding(answer, merged)
    
    return {
        "answer_bengali": answer,
        "citations": [{"chunk_id": r["id"], "scheme": r["scheme_name"]} for r in merged],
        "hallucination_check_passed": hallucination_check
    }
```

---

## 4. Testing Strategy

### 4.1 Bengali STT Evaluation Script
```python
# scripts/eval_stt.py
"""
Run weekly. Evaluates STT accuracy against 500 labeled Bengali audio samples.
Samples cover: Murshidabad dialect, South 24 Parganas dialect, 
financial vocabulary, number words, product names.
"""
import jiwer  # pip install jiwer

def evaluate_stt(test_samples: list[dict]) -> dict:
    hypotheses = []
    references = []
    
    for sample in test_samples:
        result = asyncio.run(transcribe_bengali(load_audio(sample["audio_path"])))
        hypotheses.append(result["transcript"])
        references.append(sample["ground_truth"])
    
    wer = jiwer.wer(references, hypotheses)
    cer = jiwer.cer(references, hypotheses)
    
    print(f"WER: {wer:.3f} ({wer*100:.1f}%)")
    print(f"CER: {cer:.3f} ({cer*100:.1f}%)")
    
    # Push to Prometheus
    push_metric("stt_word_error_rate", wer)
    
    return {"wer": wer, "cer": cer}
```

### 4.2 RAG Hallucination Audit Script
```python
# scripts/audit_rag.py
"""
Run weekly. Pulls 50 random scheme Q&As from production logs.
A human reviewer checks each: does the answer match the cited document?
"""
def generate_audit_report(week_start: date) -> str:
    samples = fetch_random_rag_interactions(week_start, n=50)
    
    report_lines = [f"RAG Audit Report — Week of {week_start}\n{'='*50}"]
    
    for i, sample in enumerate(samples, 1):
        report_lines.append(f"\n{i}. Query: {sample['query']}")
        report_lines.append(f"   Answer: {sample['answer'][:200]}...")
        report_lines.append(f"   Citations: {sample['citations']}")
        report_lines.append(f"   [ ] GROUNDED  [ ] HALLUCINATION  [ ] UNCERTAIN")
    
    return "\n".join(report_lines)
```

---

## 5. Pilot Deployment Plan (Week 18)

### 5.1 Pilot Scope
- 2 NGO partners (Murshidabad + South 24 Parganas)
- 10 SHG groups per district = 100–200 women
- Duration: 4 weeks before assessing go/no-go for Phase 2
- Support: WhatsApp group with product team + NGO coordinator

### 5.2 Pilot Onboarding Process
1. NGO coordinator shares bot number in existing SHG WhatsApp groups
2. Women text "শুরু" to start onboarding
3. First week: Voice-Ledger only (reduce cognitive load)
4. Week 2: Scheme RAG unlocked
5. Week 3–4: All MVP features active

### 5.3 Pilot Success Criteria
| Metric | Target |
|--------|--------|
| Onboarding completion | ≥ 70% of women who start |
| Week 2 retention (at least 1 ledger entry in week 2) | ≥ 50% |
| Ledger entries per active user per week | ≥ 3 |
| Scheme checklists requested | ≥ 30 total |
| NPS (collected via WhatsApp survey at week 4) | ≥ 40 |
| Critical bugs reported | 0 data loss; < 5 UX blockers |

### 5.4 Rollback Plan
- If STT accuracy drops below 80% in production: auto-failover to Whisper
- If any user reports data loss: freeze ledger writes; manual audit before resuming
- If WABA suspended: pre-prepared template explaining the situation; Gupshup backup number
