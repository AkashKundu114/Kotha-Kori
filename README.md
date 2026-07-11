# Kotha-Khata (কথা-খাতা)

Voice-first WhatsApp bot for West Bengal SHG women — bookkeeping, product
catalog creation, and market intelligence, entirely in spoken Bengali.

This is the **trimmed, production-oriented build**: only the three pilot
features are implemented (Voice-Ledger, Catalog Creator, Market Predictor).
Messaging runs exclusively on the **official Meta WhatsApp Cloud API** — no
Twilio, no Baileys, no other third-party messaging provider.

**AI vendors, and why each one:**
- **Sarvam AI** (`sarvam-30b`) — cheap, Bengali-native primary tier for every
  structured text task: ledger extraction, corrections, market phrasing,
  ad captions, and Bengali↔English translation. This is where most of your
  spend should land. Fully optional — leave `SARVAM_API_KEY` blank and
  everything still works, just routed to OpenAI instead at higher cost.
- **OpenAI** (`gpt-4o-mini` for vision, `whisper-1` for STT) — the only
  vision-capable vendor here (Sarvam has no general product-photo vision
  model; "Sarvam Vision" is document/OCR intelligence, a different tool),
  and the quality-escalation tier when Sarvam's output fails to parse or
  self-reports low confidence.
- **Self-hosted fallback** (optional, off by default) — a generic local
  chat model via Ollama, and/or your own Q4-quantized `sarvam-translate`
  box served OpenAI-compatible, for zero-marginal-cost uptime once you've
  provisioned a GPU.

## What's here

| Feature | What it does |
|---|---|
| **Voice-Ledger** | Bengali voice note → Banglish/code-mixed normalization (only when needed — cheap heuristic gates the translation call) → structured income/expense extraction → confirm/correct loop → database write → bank-submittable PDF |
| **Catalog Creator** | Product photo → background removal → vision product ID (OpenAI) → dual Bengali captions (warm WhatsApp message + short ad copy, via Sarvam) → price suggestion → optional privacy-respecting market-demand note → composited into a single shareable **ad poster image** (falls back to photo + separate captions if no Bengali font is installed) |
| **Market Predictor** | k-anonymized (min. 5 distinct sellers) aggregation of ledger sales data by block, fused with optional mandi price data, into rising/saturated trend advice |
| **General conversation** | Off-topic messages get a real, warm, cheap (Sarvam-routed) reply that gently steers back on-topic, instead of a static canned redirect |

Government Scheme RAG, agri-diagnostics, meeting minutes, training, and the
subsidy matchmaker from the original 8-feature PRD are **not** in this build.

## Quick start

```bash
make setup     # copies .env.example -> .env, checks it, brings up Postgres
# now edit .env — fill in the REQUIRED section (see below)
make dev       # docker compose up --build
```

That's it — Postgres schema is applied automatically on first boot
(`migrations/0001_init.sql`), no separate migration step needed.

Run the test suite any time (no API keys or network required):
```bash
make test
```

## What you must provide

Two things are required to run this at all:

1. **A WhatsApp Cloud API app** (Meta Developer account → WhatsApp product →
   Phone Number ID + Access Token + App Secret + a verify token you choose
   yourself). See `SETUP.md` for the exact click-through.
2. **An OpenAI API key.**

Strongly recommended (cuts per-message cost significantly, see
`docs/COST.md`): a **Sarvam AI key** (`sarvam.ai`, has a free ₹100 signup
credit). Everything else in `.env.example` (S3 bucket, Langfuse, mandi price
API, local-model fallback, Bengali font for poster generation) is optional.

## Architecture, in one paragraph

`services/gateway` is the FastAPI webhook receiver — it verifies Meta's HMAC
signature, deduplicates retried webhooks, rate-limits per number, and hands
off to Celery so the 20-second WhatsApp ack window is never at risk.
`services/orchestrator` is a LangGraph state machine (Postgres-checkpointed,
so every conversation turn is resumable) with one node per feature.
`services/orchestrator/model_router.py` is the single place any LLM/vision/
translation call goes through — a Sarvam → local-model → OpenAI cost cascade
for text, OpenAI-only for vision, all with retries and hard timeouts, raising
a typed `ModelUnavailableError` that every node catches and turns into a
friendly Bengali message instead of a crash.

Full design rationale: see `docs/SECURITY.md` for what's hardened and why.
Step-by-step first-run instructions: see `SETUP.md`.

## Repository layout

```
services/
  gateway/             FastAPI WhatsApp webhook + request boundary
  orchestrator/         LangGraph state machine, feature nodes, model router
                         (Sarvam -> local -> OpenAI cascade)
  translation_service/  Sarvam client (translate + chat + self-hosted fallback)
  voice_gateway/         OpenAI Whisper -> self-hosted faster-whisper STT cascade
  pdf_service/           Bank-submittable monthly report generation
  vision_service/        Catalog image processing, dual captions, ad-poster composite
  market_service/        k-anonymized market trend aggregation
shared/
  config/ db/ observability/ storage/ whatsapp/
assets/fonts/          Bengali TTF for poster text overlay (you provide the file)
migrations/            Single init SQL, applied automatically on first boot
tests/unit/            Fast, offline tests for the security-critical logic
```

## License

AGPLv3 — see `LICENSE`.
