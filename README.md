# Kotha-Khata v2 (কথা-খাতা)
### Voice-Ledger & Growth Assistant for West Bengal SHG Women

A WhatsApp-native AI agent that turns spoken Bengali into structured financial
records, hallucination-checked government scheme guidance, and group governance
documents — no app download, no literacy required.

**This is a re-architected v2 of the original plan.** If you're new to the project,
read `docs/ARCHITECTURE.md` first — it explains exactly what changed from the
original PRD/TRD/Roadmap and why, with the supporting research in
`docs/research/agent_frameworks.md`.

## What's different from a typical "voice bot + RAG" project

| Layer | Approach |
|---|---|
| Conversation orchestration | **LangGraph** state machine, Postgres-checkpointed — not a keyword router + scattered Celery tasks |
| Voice (STT/TTS) | **3-tier cascade**: Sarvam AI → Bhashini → self-hosted fine-tuned Whisper |
| Structured input (onboarding, eligibility) | **WhatsApp Flows** — native forms, no LLM round-trip needed |
| LLM usage | **Cascaded by task criticality**: Claude for safety-critical scheme answers, self-hosted Qwen for routine extraction, auto-escalation on low confidence |
| RAG hallucination prevention | Real **two-pass grounding verifier** (assertion extraction + context check), not a hardcoded `True` |
| Retrieval | **Hybrid**: Postgres full-text search + pgvector, fused via reciprocal rank fusion |
| Observability | **Langfuse**, self-hosted, traces every node and model call |

## Quick Start

```bash
git clone <this-repo>
cd kotha-khata-v2
cp .env.example .env          # fill in WA_*, SARVAM_API_KEY, ANTHROPIC_API_KEY, etc.
make setup                    # infra + migrations + hybrid search index
make pull-models               # self-hosted fallback tier models
make seed-schemes              # ingest government scheme PDFs (see data/schemes/raw/)
make dev                       # docker compose up --build
```

Open `http://localhost:3000` for the Langfuse trace dashboard once a few
messages have flowed through.

## Repository Map

```
services/
  gateway/            FastAPI webhook — verifies Meta signature, transcribes if
                       needed, hands off to the orchestrator. No business logic.
  orchestrator/        <-- START HERE. The LangGraph brain.
    graph.py            the StateGraph wiring (single source of truth for what
                         features exist and how they connect)
    state.py             typed conversation state
    model_router.py      Claude vs self-hosted Qwen cascade
    nodes/                one file per feature node
  voice_gateway/        3-tier STT cascade + providers/{sarvam,bhashini,whisper_local}
  rag_service/          hybrid retrieval + the grounding verifier
  pdf_service/          unchanged from v1 — WeasyPrint report generation
shared/
  config/settings.py    all environment configuration
  whatsapp/             Meta API client (sender, parser, media download)
  observability/        Langfuse tracing wrapper
docs/
  ARCHITECTURE.md       <-- READ THIS SECOND, after this README
  research/              the 2026 research backing each architecture decision
  PRD.md / TRD.md / ROADMAP.md / APP_FLOW.md   (carried over from v1 — the
                         product vision, personas, and feature specs are still
                         valid; only the technical implementation changed)
tests/
  unit/test_grounding_verifier.py   a good first PR: extend this
migrations/
  0002_hybrid_search.sql            the FTS index v1's schema never actually got
```

## License
AGPLv3 (carried over from v1 — appropriate for a publicly-funded social-impact
network service; see `LICENSE`).
