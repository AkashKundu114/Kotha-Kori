# Kotha-Khata (কথা-খাতা)

**Voice-first bookkeeping, government-scheme guidance, catalog creation, and market intelligence for West Bengal Self-Help Group women — delivered entirely through WhatsApp, in spoken Bengali.**

> *"Kotha-Khata"* combines *kotha* (কথা, "speech/word") and *khata* (খাতা, "ledger/notebook") — a spoken-word ledger. The barrier this project targets is not capability, it is translation: between what rural micro-entrepreneurs already do and know (spoken Bengali, everyday business) and what the formal system accepts (structured text, documented records, bank-submittable proof). Kotha-Khata is that translator.

This is not a generic chatbot wrapper around an LLM. It is a systems project built around a real accessibility gap, with the engineering decisions, product scope, safety posture, and research design all documented as first-class artifacts alongside the code — so the repository is reviewable end-to-end in a conference, interview, or portfolio setting, not just runnable.

---

## Table of Contents

- [The Problem](#the-problem)
- [Who This Is For](#who-this-is-for)
- [Start Here — Documentation Map](#start-here--documentation-map)
- [What Is Built](#what-is-built)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Repository Layout](#repository-layout)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Testing & Quality](#testing--quality)
- [Safety, Security & Privacy](#safety-security--privacy)
- [Evaluation & Metrics](#evaluation--metrics)
- [Roadmap](#roadmap)
- [Why This Is Portfolio-Ready](#why-this-is-portfolio-ready)
- [License](#license)

---

## The Problem

Rural Self-Help Group (SHG) women in West Bengal run real, capable micro-businesses — pickle and papad production, Kantha embroidery, poultry rearing, vegetable cultivation, jute weaving — but the formal financial and welfare system is effectively closed to them:

| Gap | Current reality | Cost |
|---|---|---|
| Bookkeeping | Manual ledger or none at all | Ineligible for bank-linkage loans; no visibility into actual profit |
| Government scheme access | Word-of-mouth, Panchayat office visits | An estimated 40–60% of eligible women never apply |
| Marketing | No materials, sales limited to word-of-mouth | Products chronically underpriced; market stays hyperlocal |
| Agricultural risk | Nearest agronomist is 15–30 km away | A single crop or livestock loss can wipe out an entire investment |
| Meeting records | Handwritten minutes, or none | SHGs lose "graded" status; bank linkage gets severed |
| Market intelligence | None | Overproduction of low-margin goods; wasted capital |

General-purpose AI chatbots assume literacy, English or formal Hindi, and sustained screen attention. Government portals assume Aadhaar-linked logins and bureaucratic form literacy. Standalone apps see 80%+ drop-off because they require a download and habit formation. WhatsApp, by contrast, already has near-universal adoption in this demographic — no new behavior is required to reach people where they already are.

## Who This Is For

The product is designed around three personas, detailed in full in [`docs/product.md`](docs/product.md):

- **Sunita (primary)** — a 28–55 year-old SHG member running 1–3 micro-businesses, with limited or functional literacy, an Android phone on 2G/3G connectivity, and no way to prove income for a loan or to know which scheme she qualifies for.
- **Rina (secondary)** — an SHG president/secretary who spends 45+ minutes handwriting meeting minutes, where errors cause re-grading delays with the block office.
- **Block-level NGO coordinator (tertiary)** — oversees 50–200 SHGs and has no single source of truth for group activity across a block.

## Start Here — Documentation Map

The `docs/` directory is curated to be conference- and interview-ready. Each file has a distinct job:

| File | Why it matters |
|---|---|
| [`docs/portfolio.md`](docs/portfolio.md) | Recruiter/interview-facing case study — the five engineering decisions most worth discussing live, written scope-honestly (what's built vs. what's vision). |
| [`docs/architecture.md`](docs/architecture.md) | System design record: what changed between the v1 plan and the current v2 implementation, and *why* — read this before touching any code. |
| [`docs/product.md`](docs/product.md) | Full PRD: problem statement, personas, feature specs (FR/AC), non-functional requirements, and regulatory posture. |
| [`docs/security.md`](docs/security.md) | Structured, file-specific security audit with severity-ranked findings and fixes. |
| [`docs/red-team.md`](docs/red-team.md) | An independent, adversarial second audit pass that found issues the first one missed. |
| [`docs/research.md`](docs/research.md) | User model, evaluation methodology, and pilot research plan. |
| [`docs/fieldwork.md`](docs/fieldwork.md) | Consent language, interview guides, and field-study materials for real-world piloting. |
| [`docs/roadmap.md`](docs/roadmap.md) | 18-month phased roadmap: Foundation → MVP → Growth → Scale, sprint-by-sprint. |

Historical planning notes, superseded implementation plans, and earlier draft material live in [`docs/archive/`](docs/archive/) — preserved for traceability, deliberately kept out of the primary reading path so a first-time reader isn't forced to wade through every sprint note.

## What Is Built

Scope-honesty is treated as part of the engineering discipline here: the original PRD specifies eight features, and the current pilot deliberately implements a subset well rather than everything shallowly.

| Feature | Status | What it actually does |
|---|---|---|
| **Voice-Ledger** | ✅ Built, tested | Bengali voice note → entity extraction → confirm/correct loop → database write → bank-submittable PDF profit/loss statement. |
| **Catalog Creator** | ✅ Built, tested | Product photo → background removal → vision-model classification → Bengali sales caption generation → price suggestion. |
| **Market Predictor** | ✅ Built, tested | k-anonymized aggregation of ledger sales data by block, fused with Agmarknet mandi price signals, into rising/saturated demand classifications. |
| **Government Scheme RAG** | ⚙️ Code-complete, held out of pilot routing | Hallucination-guarded eligibility Q&A over official West Bengal scheme documents (Lakshmir Bhandar, Anandadhara, Kanyashree, SVSKP, Krishak Bandhu, and more), deliberately kept behind remaining safety checks before going live — see [System Architecture](#system-architecture). |
| **Loan/subsidy matchmaker, meeting minutes, micro-skill training, agri-diagnostics** | 📋 Specified in the PRD, not current pilot scope | Full functional requirements and acceptance criteria exist in [`docs/product.md`](docs/product.md); intentionally deferred past the 2-week pilot wedge per [`docs/roadmap.md`](docs/roadmap.md). |

## System Architecture

The full design-decision record — including what was tried, what broke, and why it changed — lives in [`docs/architecture.md`](docs/architecture.md). The highlights:

**Orchestration.** Conversation flow is a single **LangGraph `StateGraph`** (`services/orchestrator/graph.py`) rather than a keyword router dispatching into independent Celery tasks. State is a typed object, checkpointed to Postgres, so every conversational turn is resumable, replayable, and inspectable — not something reconstructed by reading Redis by hand at 2am. Celery is retained only as the execution substrate underneath LangGraph, so a slow node never blocks WhatsApp's 20-second webhook acknowledgement window.

**Voice pipeline.** A three-tier STT/TTS provider cascade (`services/voice_gateway/provider_cascade.py`):
1. **Sarvam AI** (`saarika` STT / `bulbul` TTS) — primary, best accuracy and latency on dialectal Bengali.
2. **Bhashini** — fallback on error, timeout, or budget cap; free, government-backed.
3. **Self-hosted fine-tuned `faster-whisper`** — final fallback, zero marginal cost, works even if paid APIs are unreachable.

**Structured input.** Onboarding and eligibility intake use **WhatsApp Flows** (native tap-to-select forms) rather than round-tripping structured yes/no data through STT and an LLM call per turn. Voice stays the primary channel for genuinely unstructured speech — the ledger, catalog descriptions, meeting summaries.

**LLM routing by consequence, not by task type.** `services/orchestrator/model_router.py` sends safety-critical output (scheme eligibility verdicts, RAG generation/verification) to Claude every time, while routine high-volume tasks (ledger NER, intent classification) run on a self-hosted, fine-tuned **Qwen2.5-7B via Ollama** — escalating to Claude automatically when the local model's self-reported confidence drops below a threshold. That threshold is personalized per user based on historical correction rate, so a user the system has previously gotten wrong faces a stricter bar before the cheap model is trusted on her again.

**RAG hallucination prevention.** Retrieval is hybrid — Postgres full-text search fused with `pgvector` cosine similarity via reciprocal rank fusion — feeding a genuine two-pass verifier (`services/rag_service/grounding_verifier.py`) rather than a hardcoded "passed" flag:
1. Extract every number, date, scheme name, and amount asserted in the generated Bengali answer.
2. Verify each assertion is actually present in the specific retrieved chunk it claims to come from — not just present *somewhere* in the combined context.

This catches a specific, dangerous failure mode nicknamed a **citation-shaped hallucination**: if Scheme A's real chunk says ₹1,000 and a different retrieved chunk (for Scheme B) happens to mention ₹2,500, a naive "is this number anywhere in context" check would let "Scheme A gives ₹2,500" pass — the number *is* present, just attached to the wrong scheme. The verifier matches each numeric assertion to the scheme named nearest to it via an alias table (Bengali and Latin script), so cross-scheme mixups are caught rather than silently shipped. Nine unit tests in `tests/unit/test_grounding_verifier.py` cover this directly, including a swapped-amount case and a correctly-attributed multi-scheme comparison that should still pass.

**Observability.** Self-hosted **Langfuse** wraps every LangGraph node and LLM call — chosen specifically so a multi-step, multi-provider agent is debuggable from trace data in week one, not guessed at from raw logs.

**What deliberately stayed the same:** `pgvector` co-located with Postgres instead of a separate vector database (still correct at this corpus scale), WeasyPrint for PDF generation, and a FastAPI + Redis + Postgres core sized for this team.

## Technology Stack

| Layer | Choices |
|---|---|
| API & orchestration | FastAPI, LangGraph + `langgraph-checkpoint-postgres`, Celery |
| Data | PostgreSQL 16 with `pgvector`, Redis (sessions, rate limiting, dedup), SQLAlchemy (async) |
| LLM / ML | Claude (safety-critical path), self-hosted Qwen2.5-7B via Ollama (routine path), `faster-whisper` (offline STT fallback), Sarvam AI + Bhashini (primary/fallback STT & TTS) |
| Vision | `rembg` / ONNX Runtime for background removal, vision classification for the catalog feature |
| Documents | WeasyPrint + Jinja2 for Bengali-Unicode PDF generation (bank-submittable ledger reports) |
| Storage | S3-compatible object storage (`boto3`) |
| Observability | Langfuse (self-hosted), Prometheus-style business metrics |
| Messaging | WhatsApp Cloud API (webhooks, media, WhatsApp Flows) |
| Infra | Docker Compose (local/pilot), Kubernetes manifests + Terraform scaffolding (`infrastructure/`), Caddy as reverse proxy/TLS terminator |
| Quality | `pytest` + `pytest-asyncio`, `ruff`, `mypy` |

## Repository Layout

```text
services/
  gateway/          FastAPI WhatsApp webhook and request boundary
  orchestrator/     LangGraph state machine and feature nodes (start here to see what exists)
  voice_gateway/    Sarvam -> Bhashini -> Whisper STT/TTS cascade
  rag_service/      Hybrid retrieval and the grounding verifier
  pdf_service/      Monthly bank-submittable report generation
  market_service/   Market data aggregation with k-anonymity enforcement
  vision_service/   Catalog image processing
  stt/              Legacy standalone Whisper service, retained for reference only

shared/
  config/           Environment settings
  db/               SQLAlchemy models and sessions
  observability/    Tracing helpers
  storage/          S3-compatible storage client
  whatsapp/         Meta API parsing, media handling, and sending

ml/
  llm/              QLoRA and Ollama model assets
  whisper/          Whisper fine-tuning scripts
  vision/           Vision model data placeholder
  ner/              Bengali NER data placeholder

docs/               Curated, conference-ready documentation (see the map above)
docs/archive/       Preserved planning notes, drafts, and historical decisions
tests/              Unit tests and fixtures
scripts/            Operational scripts (scheme seeding, RAG audit, STT eval)
migrations/         Versioned SQL migrations
infrastructure/     Docker, Kubernetes, and Terraform deployment scaffolding
```

## Quick Start

```bash
cp .env.example .env
make setup          # installs deps, brings up Postgres/Redis, runs migrations
make seed-schemes   # ingests government scheme documents into the RAG index
make dev            # docker compose up --build — starts every service
```

Pull the local LLM/embedding models used by the cost-aware router:

```bash
make pull-models    # ollama pull qwen2.5:7b-instruct-q4_K_M + nomic-embed-text
```

Run the quality gate:

```bash
make test    # pytest tests/ -v — start with tests/unit/test_grounding_verifier.py
make lint    # ruff check . && mypy shared/ services/
```

Run `make help` at any time for the full list of commands.

## Configuration

All configuration lives in `.env`, seeded from [`.env.example`](.env.example). Notable settings:

- **WhatsApp Cloud API** — `WA_PHONE_NUMBER_ID`, `WA_ACCESS_TOKEN`, `WA_WEBHOOK_VERIFY_TOKEN`, `WA_APP_SECRET`.
- **Voice providers** — `SARVAM_API_KEY` with a configurable monthly budget cap (`SARVAM_MONTHLY_BUDGET_INR`), plus Bhashini credentials for the fallback tier.
- **LLM routing** — `OPENAI_API_KEY`/`OPENAI_MODEL` for the safety-critical path, `USE_LOCAL_MODELS` + `OLLAMA_BASE_URL` for the routine path, and `ROUTINE_CONFIDENCE_FLOOR` for the escalation threshold.
- **Storage** — S3-compatible bucket/region/endpoint configuration (deployed against DigitalOcean Spaces by default).
- **Data sources** — `DATA_GOV_IN_API_KEY` for market/mandi price signals.

No third-party credential is required to explore the repository's architecture, tests, or documentation — only to run the full live stack against real WhatsApp traffic.

## Testing & Quality

- Unit tests live under `tests/unit/`, with `tests/unit/test_grounding_verifier.py` as the recommended entry point — it's small, self-contained, and demonstrates adversarial thinking about the system's own RAG safety layer (a reproduced hallucination bug, its fix, and nine regression tests covering swapped-amount and word-form-number cases).
- `ruff` and `mypy` run across `shared/` and `services/` as the lint/type-check gate.
- `scripts/audit_rag.py` supports a weekly human audit workflow for RAG hallucination rate.
- `scripts/eval_stt.py` supports automated word-error-rate evaluation against a labeled Bengali sample set.

## Safety, Security & Privacy

Security is treated as an explicit, versioned engineering artifact rather than an afterthought:

- [`docs/security.md`](docs/security.md) is a structured, file-specific audit — findings are tied to exact files and exploit paths (e.g., missing webhook idempotency causing duplicate financial records, unenforced rate limiting enabling cost-exhaustion, and gaps between documented data-retention promises and actual code behavior), each with a severity ranking and a concrete fix.
- [`docs/red-team.md`](docs/red-team.md) is an independent second pass, run specifically to find what the first audit missed — including issues like SSRF risk in the PDF renderer via unescaped LLM-generated content, and infrastructure services bound without authentication.
- **Privacy-by-construction in market intelligence:** the aggregator enforces a minimum sample size (`MIN_SAMPLE_SIZE = 5`) at the query level via `HAVING COUNT(DISTINCT ...) >= :min_sample`, not as an afterthought filter — no block/product trend is ever reported unless at least five distinct sellers contributed, because each data point represents a vulnerable individual's income.
- **Financial and medical guardrails:** the bot is explicitly scoped as an information and record-keeping tool, never a registered financial advisor or medical diagnostician; disclaimers are mandatory in-product, per [`docs/product.md`](docs/product.md) §9.
- The bot never asks for Aadhaar numbers, bank account numbers, or OTPs at any point.

## Evaluation & Metrics

Evaluation is designed to be outcome-grounded, not just NLP-metric-grounded — most comparable systems report task accuracy alone; this project deliberately also tracks whether the tool produced a real-world result.

| Metric | Method | Target |
|---|---|---|
| Bengali STT word error rate, by dialect | Weekly automated eval against a labeled sample set | ≤ 92% WER on rural Bengali |
| Ledger extraction accuracy | Correction-rate proxy + manual audit of 100 samples | ≥ 88% |
| RAG hallucination rate | Grounding-verifier output logged per query, weekly human audit of 50 samples | Zero tolerated in manual audit |
| Real-world outcome: bank-accepted PDF | Day-14/30 WhatsApp follow-up survey | Tracked, not assumed |
| Real-world outcome: scheme application submitted | Same survey pattern, `scheme_interactions.user_confirmed_applied` | Tracked |

Full methodology, including the user research model and pilot design, is in [`docs/research.md`](docs/research.md).

## Roadmap

The 18-month roadmap is organized as three concentric rings of value, detailed sprint-by-sprint in [`docs/roadmap.md`](docs/roadmap.md):

- **Ring 1 — MVP:** prove the core loop (voice transaction → bank-showable PDF). The wedge.
- **Ring 2 — Growth:** schemes, catalog, agri-diagnostics, meeting minutes. The retention engine.
- **Ring 3 — Scale:** market intelligence and training features that improve with network volume. The moat.

## Why This Is Portfolio-Ready

The repository foregrounds exactly what reviewers look for: scoped product thinking backed by a real PRD, explicit service boundaries and orchestration decisions with documented tradeoffs, a reproducible local setup, two independent rounds of security review, and an honest, visible distinction between implemented pilot features and long-term product vision. [`docs/portfolio.md`](docs/portfolio.md) is written specifically as an interview-facing case study walking through the five decisions most worth discussing live — LangGraph orchestration, criticality-based LLM routing, the citation-shaped hallucination fix, the two-pass security audit, and privacy-by-construction in market intelligence. The archive keeps the full decision trail available without forcing a first-time reader to wade through every sprint note.

## License

AGPLv3 — a deliberate choice for a publicly-funded, social-impact network service: the network-copyleft clause means anyone who forks this and runs it as a hosted service owes the modified source back to their users. See [`LICENSE`](LICENSE).
