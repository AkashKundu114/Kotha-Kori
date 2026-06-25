# Kotha-Kori (কথা-কড়ি)
## Technical Requirements Document (TRD)
**Version:** 1.0 | **Status:** Approved for Engineering | **Date:** June 2026

---

## 1. System Architecture Overview

Kotha-Khata is a **serverless-first, event-driven WhatsApp AI platform** with four primary subsystems:

1. **Gateway Layer** — WhatsApp message ingestion, session routing, rate limiting
2. **AI Processing Layer** — STT, NLU, RAG, Vision, TTS pipelines
3. **Data Layer** — User ledgers, scheme knowledge base, group records, market data
4. **Delivery Layer** — Response assembly, PDF generation, WhatsApp message dispatch

```
┌──────────────────────────────────────────────────────────────┐
│                    USER (WhatsApp)                           │
└───────────────────────┬──────────────────────────────────────┘
                        │ HTTPS Webhook (WhatsApp Cloud API)
┌───────────────────────▼───────────────────────────────────────┐
│               GATEWAY LAYER                                   │
│  ┌─────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │  Webhook Router │  │ Session Manager│  │ Rate Limiter   │  │
│  │  (FastAPI)      │  │ (Redis)        │  │ (Redis/Upstash)│  │
│  └────────┬────────┘  └────────────────┘  └────────────────┘  │
└───────────┼───────────────────────────────────────────────────┘
            │ Async Task Queue (Celery + Redis)
┌───────────▼──────────────────────────────────────────────────┐
│               AI PROCESSING LAYER                            │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐    │
│  │  STT     │  │  NLU /   │  │  Vision  │  │  RAG       │    │
│  │  Service │  │ Intent   │  │  Service │  │  Engine    │    │
│  │(Bhashini │  │ Classify │  │(GPT-4V / │  │(LlamaIndex │    │
│  │ Whisper) │  │(Claude)  │  │ Gemini)  │  │ + PGVector)│    │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘    │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────────────┐  │
│  │  TTS     │  │ Entity   │  │  Response Orchestrator     │  │
│  │  Service │  │Extraction│  │  (LangGraph / Custom FSM)  │  │
│  │(Bhashini)│  │  (NER)   │  │                            │  │
│  └──────────┘  └──────────┘  └────────────────────────────┘  │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                    DATA LAYER                                │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │ PostgreSQL  │  │  pgvector    │  │  Redis           │     │
│  │ (User data, │  │  (RAG        │  │  (Sessions,      │     │
│  │  Ledgers,   │  │  embeddings) │  │  Rate limits,    │     │
│  │  Groups)    │  │              │  │  Cache)          │     │
│  └─────────────┘  └──────────────┘  └──────────────────┘     │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐                           │
│  │  S3 / GCS   │  │  TimescaleDB │                           │
│  │  (PDFs,     │  │  (Market     │                           │
│  │  Audio,     │  │  price time  │                           │
│  │  Images)    │  │  series)     │                           │
│  └─────────────┘  └──────────────┘                           │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                  DELIVERY LAYER                              │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │  PDF Generator  │  │ Image Proc.  │  │ WhatsApp Cloud │   │
│  │  (WeasyPrint /  │  │ (Pillow/     │  │ API Sender     │   │
│  │  ReportLab)     │  │ rembg)       │  │                │   │
│  └─────────────────┘  └──────────────┘  └────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

### 2.1 Backend Core

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **API Framework** | FastAPI (Python 3.11) | Async support, OpenAPI auto-docs, Python AI ecosystem |
| **Task Queue** | Celery + Redis | Decouples webhook ingestion from AI processing; prevents WhatsApp 20s timeout |
| **Session State** | Redis (Upstash for serverless) | Sub-millisecond conversation state retrieval; TTL-based cleanup |
| **Primary DB** | PostgreSQL 16 (via Supabase or AWS RDS) | ACID compliance for financial data; pgvector extension for embeddings |
| **Vector Store** | pgvector (co-located with PostgreSQL) | Eliminates separate vector DB; sufficient for ≤ 1M scheme document chunks |
| **Time-Series DB** | TimescaleDB (PostgreSQL extension) | Market price data; native time-series compression and queries |
| **Object Storage** | AWS S3 (or GCS) | PDF storage, processed images, audio cache |
| **Container Orchestration** | Kubernetes (EKS or GKE) | Horizontal scaling of AI workers; isolated namespace per service |
| **Service Mesh** | Istio (optional Phase 2) | mTLS between services; traffic management |

### 2.2 AI / ML Services

| Service | Technology | Notes |
|---------|-----------|-------|
| **Bengali STT** | Bhashini API (primary) | GoI-backed; trained on Indian languages including dialectal Bengali |
| **STT Fallback** | Fine-tuned Whisper Large v3 | Self-hosted on GPU instance; handles Bhashini outages |
| **NLU / Intent Classification** | Claude claude-sonnet-4-6 (Anthropic API) | Strong Bengali comprehension; instruction-following for FSM transitions |
| **NER / Entity Extraction** | Custom spaCy model (fine-tuned on SHG domain) + LLM fallback | Faster than LLM-only; LLM fallback for complex extractions |
| **RAG Retrieval** | LlamaIndex + pgvector | Hybrid search (BM25 + semantic) for scheme documents |
| **RAG Generation** | Claude claude-sonnet-4-6 with strict system prompt | Hallucination prevention via citation requirement |
| **Vision (Catalog)** | GPT-4o Vision or Gemini 1.5 Pro | Background removal + Bengali caption generation |
| **Vision (Agri-Diagnostic)** | Custom fine-tuned EfficientNet-B4 (hosted) | Fine-tuned on PlantVillage + West Bengal KVK disease dataset |
| **Background Removal** | rembg (U2-Net) | Self-hosted; no API cost per image |
| **Bengali TTS** | Bhashini TTS API | For voice responses on request |
| **Embeddings** | text-embedding-3-small (OpenAI) | Scheme document indexing; low cost, sufficient quality |
| **PDF Generation** | WeasyPrint (HTML→PDF) | Full Bengali Unicode support; templatable |
| **Market Price Data** | Agmarknet API (GoI) | Official mandi prices; free API |

### 2.3 WhatsApp Integration

| Component | Technology |
|-----------|-----------|
| **WhatsApp API Provider** | Meta WhatsApp Cloud API (direct) |
| **Fallback Provider** | Gupshup (for high-volume burst) |
| **Message Types Supported** | Text, Voice (OGG/OPUS), Image (JPEG/PNG), Document (PDF send only) |
| **Template Messages** | Pre-approved WABA templates for proactive notifications (Scheme Alerts, Reminders) |

### 2.4 Infrastructure

| Component | Technology |
|-----------|-----------|
| **Cloud Provider** | AWS (primary); GCP (AI services fallback) |
| **Compute** | EKS (general); EC2 G4dn.xlarge (GPU for self-hosted Whisper, EfficientNet) |
| **CI/CD** | GitHub Actions → ECR → ArgoCD |
| **Monitoring** | Prometheus + Grafana; Sentry (error tracking) |
| **Logging** | AWS CloudWatch + structured JSON logs |
| **Secrets** | AWS Secrets Manager |
| **IaC** | Terraform |

---

## 3. Database Schema

### 3.1 Users Table
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  whatsapp_number VARCHAR(15) UNIQUE NOT NULL, -- E.164 format
  name VARCHAR(255),
  shg_id UUID REFERENCES shg_groups(id),
  district VARCHAR(100),
  block VARCHAR(100),
  pin_code VARCHAR(6),
  preferred_language VARCHAR(20) DEFAULT 'bengali',
  onboarded_at TIMESTAMPTZ DEFAULT NOW(),
  last_active_at TIMESTAMPTZ,
  consent_given BOOLEAN DEFAULT FALSE,
  consent_given_at TIMESTAMPTZ,
  is_group_leader BOOLEAN DEFAULT FALSE,
  metadata JSONB -- dialect preference, skill level, etc.
);
```

### 3.2 SHG Groups Table
```sql
CREATE TABLE shg_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  district VARCHAR(100),
  block VARCHAR(100),
  gram_panchayat VARCHAR(100),
  village VARCHAR(100),
  formation_date DATE,
  grade_level INTEGER, -- 1-5 per West Bengal grading system
  total_members INTEGER,
  total_savings_inr NUMERIC(12,2) DEFAULT 0,
  bank_linkage_status VARCHAR(50), -- NONE, PHASE1, PHASE2, PHASE3
  anandadhara_linked BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.3 Ledger Entries Table
```sql
CREATE TABLE ledger_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) NOT NULL,
  entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
  entry_type VARCHAR(10) CHECK (entry_type IN ('INCOME', 'EXPENSE')) NOT NULL,
  amount_inr NUMERIC(10,2) NOT NULL,
  category VARCHAR(100), -- 'papad_sale', 'raw_material', 'transport', etc.
  description_bengali TEXT,
  description_english TEXT,
  raw_transcript TEXT, -- original voice note transcript
  source VARCHAR(20) DEFAULT 'voice', -- 'voice', 'text'
  is_corrected BOOLEAN DEFAULT FALSE,
  correction_of UUID REFERENCES ledger_entries(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  audio_file_key VARCHAR(500) -- S3 key if audio retained (< 60s)
);

CREATE INDEX idx_ledger_user_date ON ledger_entries(user_id, entry_date);
CREATE INDEX idx_ledger_category ON ledger_entries(category);
```

### 3.4 Meeting Records Table
```sql
CREATE TABLE meeting_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shg_id UUID REFERENCES shg_groups(id) NOT NULL,
  recorded_by UUID REFERENCES users(id) NOT NULL,
  meeting_date DATE NOT NULL,
  attendees_count INTEGER,
  attendees_names TEXT[], -- array of names
  savings_collected_inr NUMERIC(10,2),
  per_member_savings_inr NUMERIC(10,2),
  loans_given JSONB, -- [{member: "Sita", amount: 500, purpose: "school fees"}, ...]
  resolutions TEXT[],
  raw_transcript TEXT,
  formatted_minutes_text TEXT,
  pdf_s3_key VARCHAR(500),
  submitted_to_block BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.5 Scheme Knowledge Base (RAG Source)
```sql
CREATE TABLE scheme_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_name VARCHAR(255) NOT NULL,
  scheme_code VARCHAR(50),
  document_type VARCHAR(50), -- 'eligibility', 'benefits', 'application_process', 'documents_required'
  content_bengali TEXT,
  content_english TEXT,
  source_url VARCHAR(500),
  last_verified_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE scheme_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES scheme_documents(id),
  chunk_text TEXT NOT NULL,
  chunk_bengali TEXT,
  embedding vector(1536), -- OpenAI text-embedding-3-small
  chunk_index INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scheme_chunks_embedding ON scheme_chunks 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 3.6 User Scheme Interactions
```sql
CREATE TABLE scheme_interactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  scheme_name VARCHAR(255),
  eligibility_result VARCHAR(20), -- 'ELIGIBLE', 'INELIGIBLE', 'PARTIAL', 'UNKNOWN'
  checklist_sent BOOLEAN DEFAULT FALSE,
  checklist_sent_at TIMESTAMPTZ,
  application_reminder_sent INTEGER DEFAULT 0,
  user_confirmed_applied BOOLEAN,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.7 Market Data (TimescaleDB)
```sql
CREATE TABLE market_prices (
  time TIMESTAMPTZ NOT NULL,
  block VARCHAR(100) NOT NULL,
  district VARCHAR(100) NOT NULL,
  product_category VARCHAR(100) NOT NULL,
  avg_price_inr_per_unit NUMERIC(8,2),
  unit VARCHAR(20), -- 'kg', 'piece', 'dozen', 'meter'
  data_source VARCHAR(50), -- 'agmarknet', 'ledger_aggregate', 'manual'
  sample_count INTEGER
);

SELECT create_hypertable('market_prices', 'time');
CREATE INDEX idx_market_block_product ON market_prices(block, product_category, time DESC);
```

### 3.8 Conversation Sessions (Redis Schema)
```
KEY: session:{whatsapp_number}
TYPE: Hash
TTL: 1800 seconds (30 min inactivity timeout)

Fields:
  state: string (FSM state name, e.g., "LEDGER_AWAIT_CONFIRMATION")
  context: JSON string (partial entities collected so far)
  feature: string ("LEDGER" | "RAG" | "CATALOG" | "AGRI" | "MEETING" | "TRAINING")
  last_message_ts: ISO8601 timestamp
  conversation_history: JSON array (last 10 turns for LLM context)
  pending_data: JSON string (unconfirmed ledger entry, scheme Q&A state)
```

---

## 4. API Specifications

### 4.1 Incoming Webhook (Meta WhatsApp Cloud API)

```
POST /webhook/whatsapp
Headers:
  X-Hub-Signature-256: sha256=<HMAC>
  Content-Type: application/json

Body (simplified):
{
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "id": "wamid.xxx",
          "from": "919876543210",
          "timestamp": "1700000000",
          "type": "audio|text|image",
          "audio": { "id": "media_id", "mime_type": "audio/ogg; codecs=opus" },
          "text": { "body": "amar aaj 300 taka papad bikri hoyeche" },
          "image": { "id": "media_id", "mime_type": "image/jpeg" }
        }]
      }
    }]
  }]
}
```

**Webhook Processing Contract:**
- Acknowledge Meta within 200ms (return HTTP 200 immediately)
- Push to Celery queue for async processing
- Idempotency: check `message.id` against Redis dedup set (TTL 24h)

### 4.2 Internal Service APIs

#### STT Service
```
POST /api/v1/stt/transcribe
{
  "audio_url": "s3://kotha-khata-audio/xxx.ogg",
  "language": "bengali",
  "dialect_hint": "rarhi"
}
Response: {
  "transcript": "আজ আমি ১৫ প্যাকেট পাপড় বিক্রি করেছি ৩০০ টাকায়",
  "confidence": 0.94,
  "provider": "bhashini",
  "duration_seconds": 12.3
}
```

#### Entity Extraction Service
```
POST /api/v1/nlp/extract-entities
{
  "transcript": "...",
  "context": "LEDGER",
  "user_id": "uuid"
}
Response: {
  "intent": "RECORD_TRANSACTION",
  "entities": {
    "transactions": [
      { "type": "INCOME", "amount": 300, "item": "papad", "quantity": 15, "unit": "packet" },
      { "type": "EXPENSE", "amount": 100, "item": "dal_and_spices" }
    ],
    "date": "2026-06-24",
    "confidence": 0.91
  }
}
```

#### RAG Query Service
```
POST /api/v1/rag/query
{
  "query_bengali": "Lakshmir Bhandar-er jonyo ki ki kagoj lagbe?",
  "scheme_filter": ["Lakshmir Bhandar"],
  "user_context": { "age": 34, "has_swasthya_sathi": true }
}
Response: {
  "answer_bengali": "...",
  "citations": [{ "document_id": "uuid", "chunk_id": "uuid", "relevance_score": 0.89 }],
  "eligibility_verdict": "ELIGIBLE",
  "document_checklist": ["Aadhaar card", "Voter ID", "Bank passbook", "Ration card"],
  "hallucination_check_passed": true
}
```

---

## 5. AI Pipeline Specifications

### 5.1 STT Pipeline

```
[WhatsApp OGG/OPUS audio]
  → Download via Meta Media API
  → Convert to WAV 16kHz mono (ffmpeg)
  → Attempt Bhashini STT (timeout: 8s)
    → If success: return transcript + confidence
    → If fail/low confidence (<0.75): fallback to self-hosted Whisper
  → Language detect (confirm Bengali)
  → Normalize: remove filler words, standardize numbers ("tinsho" → "300")
  → Return transcript
```

**Bhashini Integration:**
- API: `https://dhruva-api.bhashini.gov.in/services/inference/pipeline`
- Task: `asr` with language `bn` (Bengali)
- Auth: ULCA API Key + User ID

**Fallback Whisper:**
- Model: `openai/whisper-large-v3` fine-tuned on 500h rural Bengali audio
- Hosted: EC2 G4dn.xlarge (NVIDIA T4 GPU)
- Average inference: 2.1x real-time

### 5.2 RAG Pipeline

```
[User query in Bengali]
  → Translate query to English (for embedding, optional)
  → Generate query embedding (text-embedding-3-small)
  → Hybrid retrieval:
      - Semantic: cosine similarity on pgvector (top-10)
      - Keyword: BM25 on scheme_chunks.chunk_text (top-10)
      - Reciprocal rank fusion: merge and rerank (top-5)
  → Construct prompt with:
      - Strict system prompt (no hallucination instruction)
      - Retrieved chunks as context
      - User's known attributes (age, district, etc.)
      - Conversation history (last 3 turns)
  → Claude generates Bengali response
  → Citation validation: every claim must map to a chunk_id
  → If claim cannot be grounded: response truncated, disclaimer added
  → Return to user
```

**Hallucination Prevention System Prompt (excerpt):**
```
You are a government scheme advisor for West Bengal SHG women.
RULES:
1. ONLY use information from the provided context. 
2. If the context does not contain the answer, say exactly: 
   "Ei byshe nishchit tathya nei, Panchayat-e jiggesh korun."
3. NEVER invent scheme amounts, eligibility criteria, or dates.
4. ALWAYS cite which scheme document your answer comes from.
5. Respond in simple, spoken Bengali (not formal/literary).
```

### 5.3 Vision Pipeline (Catalog Creator)

```
[User product image (JPEG)]
  → Validate: image quality check (blur detection, min resolution 300x300)
  → rembg background removal (U2-Net model, CPU-based)
  → Composite on clean gradient background (beige/white)
  → GPT-4o Vision analysis:
      - Identify product type and materials
      - Estimate quality tier (artisan/craft/food/agriculture)
      - Suggest price range (from internal pricing table)
  → Bengali caption generation (Claude claude-sonnet-4-6):
      - Product name in Bengali
      - 2-3 key selling features
      - Price suggestion
      - SHG name watermark text
      - Bengali CTA
  → Composite text overlay on image (Pillow)
  → Return processed image + caption text
```

### 5.4 Agricultural Diagnostic Pipeline

```
[User image OR voice description of symptoms]
  → If image:
      - Resize to 512x512
      - Run custom EfficientNet-B4 (fine-tuned on West Bengal crop disease dataset)
      - Top-3 predictions with confidence scores
      - If max confidence < 0.6: escalate to GPT-4o Vision
  → If voice description:
      - STT → extract symptom keywords
      - Map to disease knowledge base (keyword matching + embedding similarity)
  → Construct treatment response:
      - Disease name (Bengali common name)
      - Organic/home remedy (priority)
      - Locally available agri-shop solution (generic, not branded)
      - KVK referral threshold (if confidence < 0.7 OR severity = HIGH)
  → Append mandatory liability disclaimer
  → Return in Bengali
```

---

## 6. Conversation State Machine (FSM)

### 6.1 Global States

```
IDLE
  → [Any message] → INTENT_CLASSIFICATION

INTENT_CLASSIFICATION
  → "hisab" / "bikri" / "kharach" keywords → LEDGER_FLOW
  → "prakalpa" / "yojana" / scheme keywords → SCHEME_RAG_FLOW
  → image received → CATALOG_OR_AGRI_FLOW (disambiguate)
  → "mishon" / "sobha" keywords → MEETING_FLOW
  → "shikhte chai" / "training" → TRAINING_FLOW
  → unknown intent → CLARIFY (ask: "Apni ki janben? Hisab, Prakalpa, ba Chasha?")
```

### 6.2 Ledger Flow FSM

```
LEDGER_AWAIT_INPUT
  → voice/text received → LEDGER_EXTRACT_ENTITIES
  
LEDGER_EXTRACT_ENTITIES
  → extraction successful (confidence ≥ 0.80) → LEDGER_CONFIRM
  → extraction failed or ambiguous → LEDGER_CLARIFY

LEDGER_CONFIRM
  → user says "haan" / "thik ache" → LEDGER_SAVE → LEDGER_CONFIRM_SAVED → IDLE
  → user says "na" / correction detected → LEDGER_CORRECT → LEDGER_SAVE → IDLE
  → 90s timeout → LEDGER_DISCARD → IDLE

LEDGER_REPORT_REQUEST
  → period detected (this month / last month / custom) → LEDGER_GENERATE_PDF
  → LEDGER_GENERATE_PDF → send PDF via WhatsApp → IDLE
```

### 6.3 Scheme RAG Flow FSM

```
SCHEME_IDENTIFY
  → scheme name detected → SCHEME_COLLECT_ELIGIBILITY_DATA
  → no scheme detected → SCHEME_ASK_TOPIC
  
SCHEME_COLLECT_ELIGIBILITY_DATA
  → sequential questions (max 5) → SCHEME_CALCULATE_ELIGIBILITY
  
SCHEME_CALCULATE_ELIGIBILITY
  → ELIGIBLE → SCHEME_SEND_CHECKLIST → SCHEME_OFFER_REMINDER → IDLE
  → INELIGIBLE → SCHEME_EXPLAIN_WHY → SCHEME_SUGGEST_ALTERNATIVES → IDLE
  → INSUFFICIENT_DATA → SCHEME_ASK_MORE → (loop back)
```

---

## 7. Security Architecture

### 7.1 Data Protection

| Layer | Measure |
|-------|---------|
| **Transit** | TLS 1.3 for all external; mTLS for internal services |
| **At Rest** | AES-256 encryption on RDS; S3 SSE-KMS |
| **Audio** | Voice notes deleted from S3 within 60 seconds of transcription |
| **PII** | Name and phone number stored only in `users` table; all other tables reference by UUID |
| **Logs** | WhatsApp numbers masked to last 4 digits in all log entries |
| **Embeddings** | Scheme chunks only; no user data ever embedded |

### 7.2 Authentication & Authorization

```
WhatsApp Webhook:
  - HMAC-SHA256 signature verification (X-Hub-Signature-256)
  - IP allowlisting: Meta's published CIDR ranges only

Internal Services:
  - JWT with RS256 signing (JWKS endpoint)
  - Service accounts per component (least privilege)
  - Secrets via AWS Secrets Manager (no .env in containers)

Block Coordinator Dashboard:
  - OAuth 2.0 / Google SSO
  - Role-based: BLOCK_OFFICER, DISTRICT_OFFICER, ADMIN
  - Row-level security on PostgreSQL (block-scoped data)
```

### 7.3 WhatsApp Business Account Security

- Verified WABA (WhatsApp Business Account) with Meta
- Phone number display name: "Kotha-Khata | কথা-খাতা"
- Message retention: per WhatsApp Cloud API default (no storage beyond 30 days in Meta's infrastructure)
- Bot will NEVER ask for: Aadhaar number, bank account number, OTP, passwords

---

## 8. Scalability & Performance

### 8.1 Capacity Planning

| Metric | MVP (Month 3) | Growth (Month 9) | Scale (Month 18) |
|--------|--------------|-----------------|-----------------|
| Daily Active Users | 5,000 | 25,000 | 100,000 |
| Messages/day | 50,000 | 250,000 | 1,000,000 |
| STT calls/day | 20,000 | 100,000 | 400,000 |
| RAG queries/day | 5,000 | 25,000 | 100,000 |
| PDF generations/day | 500 | 2,500 | 10,000 |

### 8.2 Kubernetes Autoscaling

```yaml
# Gateway Service
replicas: 3 (min) → 20 (max)
autoscaling: CPU 70% OR request queue depth > 100

# AI Worker (Celery)
replicas: 5 (min) → 50 (max)
autoscaling: Celery queue depth > 500 tasks

# STT Whisper (GPU)
replicas: 1 (min) → 4 (max)
autoscaling: GPU utilization > 80%
node_selector: instance_type=g4dn.xlarge
```

### 8.3 Latency Budgets

```
WhatsApp text response:
  Webhook ACK:           < 200ms
  Intent Classification: < 500ms  (Claude API)
  Entity Extraction:     < 800ms  (spaCy local)
  DB Write:              < 100ms  (PostgreSQL)
  Response Formation:    < 300ms
  WhatsApp API Send:     < 500ms
  TOTAL:                 < 2.4 seconds P95

Voice note response:
  Audio Download:        < 1,000ms
  STT (Bhashini):        < 3,000ms
  Entity Extraction:     < 800ms
  DB Write:              < 100ms
  Response:              < 300ms
  TOTAL:                 < 5.2 seconds P95

RAG Query:
  Embedding:             < 200ms
  Vector Search:         < 50ms   (pgvector with IVFFlat index)
  LLM Generation:        < 4,000ms
  TOTAL:                 < 5 seconds P95

Image Processing (Catalog):
  Download:              < 1,000ms
  rembg:                 < 3,000ms (CPU)
  Vision API:            < 5,000ms
  Overlay + Upload:      < 500ms
  TOTAL:                 < 10 seconds P95
```

---

## 9. Monitoring & Observability

### 9.1 Key Metrics (Prometheus)

```python
# Business metrics
messages_processed_total{type="voice|text|image", feature="ledger|rag|catalog|agri|meeting"}
stt_word_error_rate_gauge  # updated weekly from eval run
rag_hallucination_events_total  # incremented on human audit flag
ledger_entries_created_total
pdf_reports_generated_total
scheme_checklists_sent_total

# Technical metrics  
whatsapp_webhook_latency_seconds{quantile="0.5|0.95|0.99"}
celery_task_runtime_seconds{task_name="..."}
bhashini_api_error_rate
openai_api_tokens_used_total
```

### 9.2 Alerting Rules

```yaml
- alert: STTHighErrorRate
  expr: bhashini_api_error_rate > 0.05
  for: 5m
  severity: critical
  action: Auto-failover to Whisper

- alert: LedgerEntryDrop
  expr: rate(ledger_entries_created_total[5m]) < (avg_over_time[1h] * 0.5)
  severity: warning
  action: PagerDuty alert

- alert: RAGHallucinationDetected
  expr: increase(rag_hallucination_events_total[1h]) > 0
  severity: critical
  action: Immediate Slack + email to ML team
```

---

## 10. Testing Requirements

| Test Type | Tool | Coverage Target |
|-----------|------|----------------|
| Unit Tests | pytest | 80% line coverage |
| Integration Tests | pytest + Docker Compose | All API endpoints |
| STT Accuracy Eval | Custom eval harness | 500-sample Bengali audio test set, weekly |
| RAG Hallucination Audit | Human review pipeline | 50 random Q&As per week |
| Entity Extraction NER | pytest + labeled test set | 200 Bengali voice transcripts |
| Load Testing | Locust | 10,000 concurrent webhook POSTs |
| Security (VAPT) | Burp Suite + manual | Before each major release |
| WABA Policy Compliance | Manual + Meta's test tool | Before launch |

---

## 11. Deployment Architecture

```
Production Environment:
  Region: ap-south-1 (Mumbai) — lowest latency for West Bengal
  Multi-AZ: 3 availability zones
  
Staging Environment:
  Region: ap-south-1
  Single-AZ, 20% capacity of production
  Uses real Bhashini API with test WABA number
  
Development:
  Docker Compose (local)
  STT: Whisper small (CPU) for cost
  LLM: Claude Haiku for cost
  WhatsApp: ngrok + Meta test number

Disaster Recovery:
  RDS Multi-AZ with automatic failover
  S3 cross-region replication (ap-southeast-1)
  Redis Sentinel for failover
  RTO: < 15 minutes
  RPO: < 5 minutes (RDS automated backups every 5 min)
```
