# Kotha-Khata (কথা-খাতা)

Voice-first WhatsApp bot for West Bengal SHG women — bookkeeping, pricing
guidance, product catalog creation, and market intelligence, entirely in
spoken Bengali.

Messaging runs exclusively on the **official Meta WhatsApp Cloud API** — no
Twilio, no Baileys, no other third-party messaging provider.

**AI vendors, and why each one:**
- **Sarvam AI** — sole external AI vendor. `sarvam-30b` for standard-tier
  structured text (ledger extraction, corrections, market phrasing, pricing
  explanations), `sarvam-105b` for higher-stakes phrasing (ad captions,
  negotiation), `sarvam-vision` for catalog photo identification, and
  `saaras:v3` for speech-to-text. **There is no OpenAI dependency anywhere
  in this codebase** — see `docs/architecture.md` §8.
- **Flux Pro** (optional) — poster-generation upgrade. Leave `FLUX_API_KEY`
  blank and posters are still generated locally via Pillow, free, always.
- **Self-hosted fallback (local Ollama, strongly recommended)** — the *only*
  fallback tier for every text/vision agent now that OpenAI has been
  removed. `faster-whisper` remains the dedicated free STT fallback
  regardless of this setting. See `docs/COST.md` for the full cascade table.

## What's here

| Feature | What it does |
|---|---|
| **Voice-Ledger** | Bengali voice note → Banglish/code-mixed normalization (only when needed) → structured income/expense extraction → confirm/correct loop → database write → bank-submittable PDF. Confirmation can be a tap-to-confirm **WhatsApp Flow** (optional, `WA_LEDGER_CONFIRM_FLOW_ID`) instead of typed হ্যাঁ/না, removing typo/mishearing risk on the way to a permanent write — see `docs/architecture.md` §10.3. |
| **Friend-style Pricing Chat** | A SELLER-facing conversational back-and-forth ("দর ঠিক করি একসাথে") to agree an asking price before a catalog poster is composed — warm, references seasonal/festival timing, never lets the model state a number, and hard-stops at the seller's own cost-derived floor rather than silently capping below it. See `docs/architecture.md` §10.4. |
| **Catalog Creator** | Product photo → background removal → vision product ID (Sarvam Vision, local Ollama vision fallback) → dual Bengali captions (Sarvam, dignity-guideline-constrained) → price suggestion (or the agreed price from the pricing chat above) → optional privacy-respecting market-demand note → composited into a single shareable ad poster (Flux Pro if configured, always falls back to a free local Pillow composite) |
| **Pricing Recommendation** | Deterministic price-floor/recommendation math from the seller's own cost, margin, and minimum price (`seller_profiles` table), blended with market data where available — Sarvam is used only to phrase the explanation, never to generate the number itself |
| **Negotiation** | Deterministic accept/reject against the same price floor, code-computed counter-offers (never LLM-generated), a post-generation safety scan that discards any LLM phrasing quoting below the floor, and (as of Pass 4) a deterministically-chosen negotiation *tactic* (anchor / reciprocity / value-justification / graceful walk-away — `shared/knowledge/negotiation_playbook.py`) that the LLM only phrases, never picks — see `docs/architecture.md` §9.1 and §10.4 |
| **Cross-agent verification** | `services/orchestrator/nodes/cross_verify.py` — an independent second model call checks tone/dignity, combined with a deterministic check that every ₹ figure in a composed message matches a code-computed value, before the highest-stakes pricing-chat messages are sent. See `docs/architecture.md` §10.4. |
| **Market Predictor** | k-anonymized (min. 5 distinct sellers) aggregation of ledger sales data by block, fused with optional mandi price data and the shared festival/district-mela/seasonal knowledge base, into rising/saturated trend advice |
| **General conversation** | Off-topic messages get a real, warm, cheap (Sarvam-routed) reply that gently steers back on-topic |

Government Scheme RAG (hallucination-guarded, code-complete but not wired
into V3 routing), agri-diagnostics, meeting minutes, training, and subsidy
matchmaking are **not** in this build. See `docs/archive/planning/scope.md`
for the scope-freeze rationale.

## Quick start

```bash
make setup     # copies .env.example -> .env, checks it, brings up Postgres
# now edit .env — fill in the REQUIRED section (see below)
make dev       # docker compose up --build
```

Postgres schema is applied automatically on first boot
(`migrations/0001_init.sql`, plus additive migrations for the Pricing
agent's table and SHG bank-linkage status — `0004_seller_profile.sql`,
`0005_shg_bank_linkage.sql`) — no separate migration step needed for a
fresh deploy.

Run the test suite any time (no API keys or network required):
```bash
make test
```

## What you must provide

Two things are required to run this at all:

1. **A WhatsApp Cloud API app** (Meta Developer account → WhatsApp product →
   Phone Number ID + Access Token + App Secret + a verify token you choose
   yourself). See `SETUP.md` for the exact click-through.
2. **A Sarvam AI key** (`sarvam.ai`) — this is now the sole paid AI vendor.

Strongly recommended: enable `USE_LOCAL_MODELS=true` with a self-hosted
Ollama box. With no OpenAI fallback anymore, this is the only thing that
keeps every agent alive during a Sarvam outage — see `docs/COST.md`.

Optional, and safe to leave unset: `WA_LEDGER_CONFIRM_FLOW_ID` (tap-to-confirm
ledger Flow — falls back to plain text if unset), S3 bucket, Langfuse,
mandi price API, Flux Pro, Bengali font for poster generation.

## Architecture, in one paragraph

`services/gateway` is the FastAPI webhook receiver — it verifies Meta's HMAC
signature, deduplicates retried webhooks, rate-limits per number, and hands
off to Celery so the 20-second WhatsApp ack window is never at risk.
`services/orchestrator` is a LangGraph state machine (Postgres-checkpointed,
so every conversation turn is resumable) with one node per agent.
`services/orchestrator/model_router.py` is the single place any LLM/vision/
translation call goes through — a two-tier Sarvam → local-Ollama cascade for
every agent, with retries and hard timeouts, raising a typed
`ModelUnavailableError` that every node catches and turns into a friendly
Bengali message instead of a crash. `shared/knowledge/` is the single
source of cultural/seasonal/market-timing context (festivals, district
melas, life-cycle occasions, negotiation tactics, tone/dignity rules)
every agent reads from instead of each node inventing its own.

Full design rationale: see `docs/architecture.md` (§8 for the OpenAI
removal, §10 for the shared knowledge base / dignity rules / Flow-verified
ledger / friend pricing chat / negotiation tactics / cross-verification)
and `docs/security.md` for what's hardened and why. Step-by-step first-run
instructions: see `SETUP.md`. Turn-by-turn detail on each incremental pass
that built §10's features lives in `CHANGELOG_v4_knowledge_and_dignity.md`
through `CHANGELOG_v9_district_melas.md` at the repo root — those files are
the "what changed and what's still honestly unverified" record; this
README and `docs/architecture.md` are the current-state summary.

## Repository layout

```
services/
  gateway/             FastAPI WhatsApp webhook + request boundary
                        whatsapp_flows/: scheme_eligibility_flow.json,
                        ledger_confirm_flow.json (tap-to-confirm ledger entries)
  orchestrator/         LangGraph state machine, feature nodes, model router
                         (Sarvam -> local Ollama cascade, no OpenAI)
    nodes/
      pricing_node.py       Pricing Recommendation agent — deterministic core
      negotiation_node.py   Negotiation agent — code-enforced price floor +
                             deterministic tactic selection
      price_chat_node.py    Friend-style seller pricing chat, pre-poster
      ledger_confirm_flow_node.py   Tap-to-confirm Flow consumer
      cross_verify.py       Independent second-pass dignity/numeric check
  translation_service/  Sarvam client (chat, vision, translate, self-hosted fallback)
  voice_gateway/         Saaras V3 -> self-hosted faster-whisper STT cascade
  pdf_service/           Bank-submittable monthly report generation (continuity,
                          SHG grading, declaration + sign-off line)
  vision_service/        Catalog image processing, dual captions, ad-poster composite
                          (flux_poster_client.py: optional Flux Pro tier;
                           poster_composer.py: free Pillow tier, always available)
  market_service/        k-anonymized market trend aggregation
shared/
  config/ db/ observability/ storage/ whatsapp/
  knowledge/            Shared cultural/market context: festivals, district melas,
                         life-cycle occasions, negotiation tactics, dignity rules —
                         the single source every agent reads from (docs/architecture.md §10)
  i18n/                 Bengali calendar + centralized Bengali digit/number-word helpers
assets/fonts/          Bengali TTF for poster text overlay (you provide the file)
migrations/            Init SQL + additive migrations, applied automatically on first boot
tests/unit/            Fast, offline tests for the security-critical, pricing, and
                        knowledge-base logic
```

## License

AGPLv3 — see `LICENSE`.
