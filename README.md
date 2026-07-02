# Kotha-Khata (কথা-খাতা)
### Voice-first financial ledger, government-scheme guidance, and market intelligence for West Bengal SHG women — delivered entirely through WhatsApp

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)

No app to install. No literacy required. No English or formal Bengali needed —
just a voice note in whatever dialect a user already speaks. The barrier this
project addresses isn't capability, it's translation: between what rural
Self-Help Group (SHG) women already do (run real micro-businesses, in spoken
Bengali) and what the formal financial and welfare system requires (structured,
documented, literate input). Kotha-Khata is that translation layer.

---

## Why this project is worth reading past the README

This isn't a chatbot demo. It's a systems project with real engineering
tradeoffs, a documented security posture (including a self-run red-team pass
that found what the first structured audit missed), a novel hallucination-safety
mechanism built to catch a specific and dangerous failure mode, and an honest,
written record of what's built versus what's still vision. If you're a reviewer
skimming this before a technical interview, start with
**[`docs/portfolio/PORTFOLIO_CASE_STUDY.md`](docs/portfolio/PORTFOLIO_CASE_STUDY.md)**
— it walks through the five decisions most worth discussing live.

---

## The problem, briefly

| Structural gap | Consequence |
|---|---|
| No formal bookkeeping | Ineligible for bank-linkage loans regardless of actual business health |
| Low awareness of government schemes | An estimated 40–60% of eligible women never apply |
| No marketing beyond word-of-mouth | Products underpriced, market limited to the neighborhood |
| No market intelligence | Overproduction of low-margin goods, lost capital |

General-purpose AI assistants don't close these gaps — they assume literacy, a
formal language register, and sustained engagement with a text interface this
population often doesn't have. WhatsApp already does have near-universal
adoption here. See `docs/product/PRD.md` for the full problem statement, target
personas (Sunita, Rina), and success metrics.

## Project status — what's actually built vs. what's still vision

Being precise about this distinction is itself part of the engineering
discipline here; see `docs/planning/SPRINT_V3_PLAN.md` for the full audit this
table is drawn from.

| Feature | Status |
|---|---|
| **1 — Voice-Ledger** | ✅ Built, tested, in active pilot routing — voice note → confirm/correct loop → DB write → bank-submittable PDF |
| **3 — Catalog Creator** | ✅ Built, tested, in active pilot routing — product photo → background removal → vision ID → Bengali caption → price suggestion |
| **8 — Market Predictor** | ✅ Built, tested, in active pilot routing — k-anonymized ledger aggregation + Agmarknet signal → rising/saturated trend classification |
| **2 — Scheme RAG (hallucination-guarded)** | ⚠️ Code-complete, deliberately **not** in this pilot's live routing — see the scope-cut rationale in `docs/planning/SPRINT_V3_PLAN.md` §1 |
| 4–7 — Agri-Diagnostic, Subsidy Matchmaker, Training, Meeting Minutes | 📋 Product vision only (`docs/product/PRD.md`), not built |

Current execution plan to close remaining gaps and go live:
**[`docs/planning/SPRINT_2WEEK_PLAN.md`](docs/planning/SPRINT_2WEEK_PLAN.md)**.

---

## What's different from a typical "voice bot + RAG" project

| Layer | v1 plan | v2 (this repo) — and why |
|---|---|---|
| Orchestration | Keyword router + independent Celery tasks, Redis state by convention | **LangGraph** `StateGraph`, Postgres-checkpointed — every turn resumable, replayable, inspectable. Celery kept only as execution substrate so a slow node doesn't block WhatsApp's 20s ack. |
| Voice (STT/TTS) | Bhashini-primary | **3-tier cascade**: Sarvam AI (best accuracy/latency, paid) → Bhashini (free, GoI-backed fallback) → self-hosted fine-tuned Whisper (zero marginal cost, final fallback) |
| Structured input | Voice/text round-trip through an LLM even for yes/no questions | **WhatsApp Flows** for onboarding and eligibility intake — no LLM call for structured taps |
| LLM usage | All-Claude or all-self-hosted binary switch | **Cascaded by task criticality, personalized per user** — safety-critical scheme answers always go to Claude; routine extraction goes to self-hosted Qwen2.5-7B first, with an escalation confidence-floor that tightens specifically for users the system has been wrong for before |
| RAG hallucination prevention | `"hallucination_check_passed": True` hardcoded | Real two-pass **grounding verifier** — assertion extraction (including Bengali word-form numbers) + per-chunk, scheme-attributed grounding check, catching "right number, wrong scheme" citation-shaped hallucinations |
| Retrieval | Vector-only (described, not implemented) | **Hybrid**: Postgres full-text search + pgvector, fused via reciprocal rank fusion |
| Observability | Prometheus counters only | **Langfuse**, self-hosted, traces every node and model call |
| Security | Not audited | **Two independent passes** — a structured audit (`docs/security/SECURITY_AUDIT_V3.md`) followed by an adversarial red-team pass (`docs/security/RED_TEAM_AUDIT_AND_FIXES.md`) that found CRIT-severity issues the first missed |

Full rationale for every decision above, with citations to 2026 production
practice: `docs/engineering/ARCHITECTURE.md` and `docs/research/agent_frameworks.md`.

## Security posture (a genuine differentiator, not boilerplate)

Two passes, on purpose — the second was scoped specifically to find what the
first didn't:

1. **`docs/security/SECURITY_AUDIT_V3.md`** — P0/P1/P2 triage against known
   attacker goals (corrupt financial data, burn API budget, exfiltrate PII, take
   the service down). Found: no webhook idempotency (duplicate financial
   records), no rate limiting (cost-exhaustion DoS), a written-but-uncoded audio
   deletion promise.
2. **`docs/security/RED_TEAM_AUDIT_AND_FIXES.md`** — a second, adversarial pass.
   Found: Redis/Postgres/Ollama bound to `0.0.0.0` with no auth (`redis-cli
   FLUSHALL` = instant total outage), a webhook HMAC check using the *wrong
   secret* (verify-token instead of app-secret), and an **SSRF/injection
   primitive in the PDF renderer** — unescaped, LLM-derived ledger category
   strings flowing into a Jinja2 template with autoescape off, rendered by a
   WeasyPrint process with live outbound network access.

Every finding has a concrete fix, and every fix is either applied or explicitly
tracked as open work in `docs/planning/SPRINT_2WEEK_PLAN.md` Week 1.

---

## Documentation index

This repo's `docs/` tree is organized so a new reader — engineer, recruiter, or
field researcher — can find what they need without reading everything.

| Path | What's in it |
|---|---|
| `docs/portfolio/PORTFOLIO_CASE_STUDY.md` | **Start here for a technical skim.** Recruiter/interview-facing walkthrough of the five most interesting engineering decisions. |
| `docs/engineering/ARCHITECTURE.md` | **Start here for the code.** Every v1→v2 decision, why, with a §7 addendum documenting a real bug found and fixed during a code-review pass. |
| `docs/engineering/IMPLEMENTATION_PLAN.md` | Week-by-week build plan for Phase 0–1, with real code snippets per milestone. |
| `docs/engineering/LLM_GUIDE.md` | The zero-marginal-cost self-hosted model strategy (Qwen2.5-7B, fine-tuned Whisper, Qwen2-VL) and the phased migration plan off paid APIs. |
| `docs/engineering/V3_CODE_PASS_NOTES.md` | Precise accounting of what a specific engineering pass built vs. left open — the "current state audit" every AI coding tool session should start from. |
| `docs/product/PRD.md` | Full product requirements — personas, all 8 feature specs, non-functional requirements, regulatory stance. |
| `docs/product/TRD.md` | Technical requirements — system architecture, DB schema, API specs, latency budgets, FSM design. |
| `docs/product/ROADMAP.md` | 18-month, 3-phase roadmap with risk register and dependency tracking. |
| `docs/product/APP_FLOW.md` | Every conversation flow, state-by-state, in the actual Bengali copy the bot sends. |
| `docs/product/UNIQUE_VALUE_PROPOSITION.md` | The honest "what's actually novel here vs. a generic AI wrapper" positioning doc — good source material for a paper's related-work framing. |
| `docs/security/SECURITY_AUDIT_V3.md` | Structured P0/P1/P2 security audit. |
| `docs/security/RED_TEAM_AUDIT_AND_FIXES.md` | Adversarial second-pass audit with CRIT-severity findings. |
| `docs/research/agent_frameworks.md` | 2026 production-practice research backing the architecture decisions (LangGraph vs. alternatives, hybrid RAG, provider benchmarks). |
| `docs/research/USER_MODEL_AND_RESEARCH.md` | The per-user personalization model design, plus a full research-paper field-study plan. |
| `docs/research/FIELD_RESEARCH_TOOLKIT.md` | Outreach scripts, two-tier consent forms, structured interview guide, recording protocol — ready to use in the field. |
| `docs/research/RESEARCH_PAPER_DRAFT.md` | Full paper skeleton — methodology and system description written now, results section intentionally left for real field data. |
| `docs/planning/SPRINT_V3_PLAN.md` | The scope-cut decision log (why Features 1/3/8 only) and the original 2-week plan. |
| `docs/planning/SPRINT_2WEEK_PLAN.md` | Current, execution-ready 2-week plan to close gaps and go live. |
| `docs/operations/MANUAL_TASKS_GUIDE.md` | Everything that needs a human with account access or judgment — cannot be delegated to an AI tool. |
| `docs/operations/PROJECT_GUIDE.md` | New-contributor onboarding guide, with a worked example (Day 4–5 grounding-verifier fix) and a checklist of what's done vs. what needs a human. |
| `docs/archive/original-v1-specs/README.md` | Pointer to the original v1 product specs — carried over as still-valid product truth. |

---

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

```bash
make test      # pytest tests/ -v — no network required
make lint      # ruff + mypy
```

Manual, non-code setup (Meta Business verification, Bhashini registration, GPU
provisioning, NGO partnership, consent materials) has its own multi-week
external timelines — see `docs/operations/MANUAL_TASKS_GUIDE.md` and start those
in parallel with local dev, not after.

## Repository Map

```
services/
  gateway/            FastAPI webhook — verifies Meta signature, transcribes if
                       needed, hands off to the orchestrator. No business logic.
  orchestrator/        <-- START HERE for code. The LangGraph brain.
    graph.py            the StateGraph wiring — single source of truth for what
                         features exist and how they connect
    state.py             typed conversation state
    model_router.py      Claude vs self-hosted Qwen cascade, personalized per user
    nodes/                one pure function per feature
  voice_gateway/        3-tier STT cascade + providers/{sarvam,bhashini,whisper_local}
  rag_service/          hybrid retrieval + the grounding verifier
  pdf_service/          WeasyPrint report generation
  market_service/       k-anonymized market price aggregation + external data adapters
  vision_service/       catalog image analysis / background processing
shared/
  config/settings.py    all environment configuration
  whatsapp/             Meta API client (sender, parser, media download)
  observability/        Langfuse tracing wrapper
docs/                   see the documentation index above
tests/
  unit/test_grounding_verifier.py   a good first read: 9 tests covering the
                                     citation-shaped hallucination fix
migrations/
  0002_hybrid_search.sql            the FTS index v1's schema never actually got
  0003_v3_features.sql              catalog, market, and user-model schema
```

## License

AGPLv3 — a deliberate choice for a publicly-funded, social-impact network
service: the network-copyleft clause means a fork run as a hosted service owes
its modified source back to its users. See `LICENSE`.
