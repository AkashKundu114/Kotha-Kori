# Kotha-Khata

Voice-first bookkeeping, government-scheme guidance, catalog creation, and market intelligence for West Bengal Self-Help Group women, delivered through WhatsApp.

Kotha-Khata is not a generic chatbot wrapper. It is a systems project around a real accessibility gap: rural micro-entrepreneurs often run capable businesses in spoken Bengali, while banks, welfare schemes, and formal markets require structured written records. This repo is organized to make the engineering decisions, product scope, and research posture easy to review in a conference, interview, or portfolio setting.

## Start Here

| File | Why it matters |
|---|---|
| [`docs/portfolio.md`](docs/portfolio.md) | Recruiter/interview-facing case study: five decisions worth discussing live. |
| [`docs/architecture.md`](docs/architecture.md) | System design, v1-to-v2 decisions, and the current service map. |
| [`docs/product.md`](docs/product.md) | Product requirements, personas, target users, and feature scope. |
| [`docs/security.md`](docs/security.md) | Structured security audit and remediation priorities. |
| [`docs/red-team.md`](docs/red-team.md) | Adversarial second pass that found issues the first audit missed. |
| [`docs/research.md`](docs/research.md) | User model, evaluation design, and pilot research plan. |
| [`docs/fieldwork.md`](docs/fieldwork.md) | Consent, interview, and field-study materials. |
| [`docs/roadmap.md`](docs/roadmap.md) | Phased roadmap and longer-term product direction. |

Historical planning notes, old implementation plans, and draft material live in [`docs/archive/`](docs/archive/). They are preserved for traceability but kept out of the main reading path.

## What Is Built

| Feature | Status |
|---|---|
| Voice ledger | Built: voice note to confirmation loop to database write to bank-submittable PDF. |
| Catalog creator | Built: product image processing, vision classification, Bengali captioning, and price suggestion. |
| Market predictor | Built: ledger aggregation plus Agmarknet signal for rising/saturated trend classification. |
| Scheme RAG | Code-complete but deliberately kept out of pilot routing until remaining safety checks are closed. |
| Agri-diagnostic, training, meeting minutes | Product vision, not current pilot scope. |

## Repository Layout

```text
services/
  gateway/          FastAPI WhatsApp webhook and request boundary
  orchestrator/     LangGraph state machine and feature nodes
  voice_gateway/    Sarvam -> Bhashini -> Whisper STT cascade
  rag_service/      Hybrid retrieval and grounding verifier
  pdf_service/      Monthly report generation
  market_service/   Market data aggregation
  vision_service/   Catalog image processing
  stt/              Legacy standalone Whisper service, retained for reference

shared/
  config/           Environment settings
  db/               SQLAlchemy models and sessions
  observability/    Tracing helpers
  storage/          S3-compatible storage client
  whatsapp/         Meta API parsing, media, and sending

ml/
  llm/              QLoRA and Ollama model assets
  whisper/          Whisper fine-tuning scripts
  vision/           Vision model data placeholder
  ner/              Bengali NER data placeholder

docs/               Curated portfolio and conference-ready documents
docs/archive/       Preserved planning, drafts, and historical notes
tests/              Unit tests and fixtures
scripts/            Operational scripts
migrations/         SQL migrations
infrastructure/     Deployment scaffolding
```

## Quick Start

```bash
cp .env.example .env
make setup
make seed-schemes
make dev
```

Run checks:

```bash
make test
make lint
```

## Why This Is Portfolio-Ready

The repo foregrounds the parts reviewers usually look for: scoped product thinking, service boundaries, reproducible local setup, explicit security work, and an honest distinction between implemented pilot features and long-term vision. The archive keeps the full decision trail available without forcing a first-time reader to wade through every sprint note.

## License

AGPLv3. See [`LICENSE`](LICENSE).
