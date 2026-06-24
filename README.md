# Kotha-Kori (কথা-কড়ি)
### Voice-Ledger & Growth Assistant for West Bengal SHG Women

A voice-first WhatsApp AI platform that turns spoken Bengali into structured financial records,
government scheme eligibility assessments, product marketing assets, and group governance documents.
No app download. No literacy required. Works on 2G.

---

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/your-org/kotha-khata.git
cd kotha-khata
cp .env.example .env
# → Fill in WA_PHONE_NUMBER_ID, WA_ACCESS_TOKEN, DATABASE_URL

# 2. Start infrastructure
docker compose up -d postgres redis ollama

# 3. Pull zero-cost AI models (one-time, ~10GB)
make pull-models

# 4. Run DB migrations
make migrate

# 5. Seed government scheme data
make seed-schemes

# 6. Start all services
make dev
```

## Architecture

```
WhatsApp → Gateway (FastAPI) → Celery Queue
                                    ↓
                         ┌──────────┴──────────┐
                    STT Service          AI Worker
                  (faster-whisper)    (Qwen2.5-7B)
                         │                  │
                    PostgreSQL + pgvector + Redis
```

**Zero-Cost AI Stack:**
- 🎙️ STT: fine-tuned `whisper-large-v3` (faster-whisper, self-hosted)
- 🧠 LLM: fine-tuned `Qwen2.5-7B-Instruct` via Ollama (self-hosted)
- 👁️ Vision: `Qwen2-VL-7B` + `EfficientNet-B4` (self-hosted)
- 📐 Embeddings: `nomic-embed-text` via Ollama (self-hosted)
- 📄 PDF: WeasyPrint (local)
- 🗃️ Vector DB: pgvector (PostgreSQL extension, no extra service)

**External APIs used:** WhatsApp Cloud API (Meta) only.

## Documentation

| Document | Description |
|----------|-------------|
| [PRD](docs/PRD.md) | Product requirements, user personas, feature specs |
| [TRD](docs/TRD.md) | Architecture, DB schema, API contracts, AI pipelines |
| [ROADMAP](docs/ROADMAP.md) | 18-month phased roadmap |
| [IMPLEMENTATION_PLAN](docs/IMPLEMENTATION_PLAN.md) | Sprint plan + working code |
| [APP_FLOW](docs/APP_FLOW.md) | All conversation flows + state machines |
| [ZERO_COST_LLM_GUIDE](ZERO_COST_LLM_GUIDE.md) | Full self-hosted AI guide |

## Features

| # | Feature | Status |
|---|---------|--------|
| 1 | 🎙️ Voice-Ledger (Bengali transaction recording) | MVP |
| 2 | 📋 Government Scheme RAG (hallucination-free) | MVP |
| 3 | 📸 WhatsApp Catalog Creator | MVP+ |
| 4 | 🌾 Agri-Doc & Livestock Diagnostic | MVP+ |
| 5 | 🔔 Subsidy & Loan Matchmaker (proactive) | MVP+ |
| 6 | 🎓 Micro-Skill Audio Training | Phase 2 |
| 7 | 📝 Meeting Minutes & Group Governance | MVP+ |
| 8 | 📊 Market Price & Demand Predictor | Phase 3 |

## License
MIT
