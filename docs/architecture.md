# Kotha-Khata v2 — Architecture Decisions

This document records what changed from the original plan (`docs/product.md`, `docs/archive/product/trd.md`,
`docs/roadmap.md` in the v1 repo) and **why**, based on a review of 2026 production
practice for WhatsApp AI agents, Indic-language voice pipelines, and RAG systems.
Read this before touching any code — it's the map of *why the folders are shaped this way*.

---

## 1. Orchestration: keyword-router + Celery FSM → LangGraph state machine

**v1 problem:** `services/gateway/router.py` dispatched on hand-written keyword sets
(`FINANCIAL_KEYWORDS`, `SCHEME_KEYWORDS`, ...) into independent Celery tasks that each
read/wrote Redis session state by convention. Nothing enforced that a task left the
session in a valid state; debugging "why did the bot get stuck" meant reading Redis by hand.

**v2 decision:** Replace the router + Celery-task-per-feature pattern with a single
**LangGraph `StateGraph`** (`services/orchestrator/graph.py`). Conversation state is a
typed object, persisted via LangGraph's Postgres checkpointer (not raw Redis hashes),
so every turn is resumable, replayable, and inspectable. Intent classification,
ledger entry, scheme RAG, and confirmation are *nodes* with explicit edges, not
separate Celery entrypoints. This is the dominant 2026 pattern for stateful,
branching, human-in-the-loop agents (Klarna, Replit, Elastic all run LangGraph for
this exact reason — see `docs/archive/research/agent-frameworks.md`).

Celery is **kept** only as the execution substrate (so a slow node doesn't block the
20s WhatsApp webhook ack) — LangGraph runs *inside* a Celery task, not instead of it.

## 2. Voice stack: Bhashini-primary → Sarvam-primary, free local fallback

**v1 problem:** TRD specified Bhashini as the primary STT with self-hosted Whisper as
fallback. As of 2026, independent Bengali STT benchmarks show Sarvam AI's ASR is
measurably more accurate and lower-latency on regional/dialectal Bengali than
Bhashini, while Bhashini's free tier is excellent for cost control but not built for
latency-sensitive production traffic.

**v2 decision:** `services/voice_gateway/provider_cascade.py` tries, in order:

1. **Saaras V3** (Sarvam's STT model) — primary, paid, best accuracy/latency.
2. **Self-hosted fine-tuned `faster-whisper`** — free, zero marginal cost, the only
   fallback tier (see §8 below — this is no longer an optional nicety, it's the sole
   safety net now that OpenAI has been removed entirely).

## 3. Structured input: voice-only → WhatsApp Flows for forms

**v1 problem:** Onboarding and the 5-question scheme-eligibility dialogue were both
voice/freeform-text round-trips through STT → LLM extraction → confirm. For
*structured* data (district selection, age, yes/no eligibility questions) this is
slower, costs an LLM call per turn, and is more error-prone than necessary.

**v2 decision:** Use **WhatsApp Flows** (Meta's native multi-step form UI, tap-to-select)
for onboarding and eligibility intake — see
`services/gateway/whatsapp_flows/scheme_eligibility_flow.json`. Voice stays the
*primary* channel for the ledger (genuinely unstructured speech) and for users who
prefer it everywhere, but structured branches no longer round-trip through an LLM.

## 4. LLM usage: cascaded by task criticality, Sarvam-first

**v1 problem:** The roadmap's "phased migration" implied a binary switch — pay for
a frontier model everywhere during MVP, then flip to 100% self-hosted post-pilot.
That either overpays during MVP or silently degrades quality once migrated.

**v2 decision:** `services/orchestrator/model_router.py` routes by task and by
agent tier:
- **Standard tier** (ledger NER, meeting-minutes extraction, intent classification,
  market phrasing, pricing phrasing): Sarvam-30B — cheap, Bengali-native, fast.
- **Advanced tier** (ad captions, negotiation, pricing explanations): Sarvam-105B —
  stronger reasoning for higher-stakes phrasing tasks.
- **Free fallback** (both tiers): self-hosted Qwen2.5-7B via Ollama. As of §8 below,
  this is the *only* fallback — see that section for what changed and why it matters
  more now than when it was originally "just" a cost-saving option.

## 5. RAG hallucination prevention: a hardcoded flag → a real two-pass verifier

**v1 problem:** `pipeline.py` returned `"hallucination_check_passed": True`
unconditionally. There was no actual verification step.

**v2 decision:** `services/rag_service/grounding_verifier.py` implements the
2026-standard two-pass pattern:
1. **Assertion extraction** — pull every number, date, scheme name, and amount out
   of the generated Bengali answer (regex + light NER).
2. **Grounding check** — for each assertion, verify it is actually present in the
   retrieved chunks (not just topically similar). Any ungrounded assertion forces a
   rewrite-or-refuse, never a silent pass-through.

Retrieval itself moves from vector-only to **hybrid**: Postgres full-text search
(`tsvector`/`ts_rank`, zero extra infra) fused with pgvector cosine similarity via
reciprocal rank fusion.

> **Update (Week 1, see §7.1 below):** the v2.0 grounding check above had its own
> gap — it concatenated all chunks before checking grounding, so a number from the
> *wrong* scheme's chunk could still pass as "grounded." This is now fixed.

## 6. Observability: none → Langfuse from day one

**v1 problem:** No tracing of LLM calls, retrieval quality, or conversation flow
existed in the codebase — only Prometheus counters for business metrics.

**v2 decision:** Self-hosted **Langfuse** (open source, fits the project's
cost-sensitive AGPL posture) wraps every LangGraph node and LLM call. This is what
makes a multi-step, multi-provider agent debuggable by an intern in week one instead
of guessed-at from logs.

---

## What stayed the same (and why)

- **pgvector co-located with Postgres** instead of a separate vector DB — still the
  right call at this document-corpus scale (≤1M chunks).
- **WeasyPrint for PDF** — no change needed, it already does the job well.
- **FastAPI + Redis + Postgres core** — still the right stack for this team size.
- **Domain-locked, hallucination-guarded scheme RAG as the trust anchor** — the
  core product insight from the PRD is unchanged, only how it's enforced.

---

## 7. Addendum — Week 1 intern findings (grounding verifier hardening + dead-code audit)

This section is appended, not a rewrite — see §1–6 above for the original
v1→v2 decisions. Append further dated entries here rather than editing history above.

### 7.1 Grounding verifier: per-chunk + scheme-aware checking

`services/rag_service/grounding_verifier.py` (§5 above) originally concatenated
every retrieved chunk into a single string before checking whether an
assertion's surface text appeared in it. That allows a **citation-shaped
hallucination**: if Scheme A's real chunk says ₹1000 and a *different*
retrieved chunk (for Scheme B) happens to mention ₹2500, a generation that
claims "Scheme A gives ₹2500" was marked `all_grounded: True` — ₹2500 *is*
present in the combined context, just attached to the wrong scheme.

**Fix:** grounding is now checked per-chunk, and whenever the answer names a
scheme near an assertion (using a small Bengali/Latin alias table,
`SCHEME_NAME_ALIASES`), that assertion must be found within a chunk
belonging to *that specific* scheme. Nine tests cover this in
`tests/unit/test_grounding_verifier.py`.

**Known limitation, left for a follow-up PR:** scheme-name detection is a
fixed lookback-window alias match, not a real coreference/NER pass.

### 7.2 Dead-code audit: pre-LangGraph v1 remnants still in the tree

The following v1-era files/directories were found to be **unreferenced by
anything in the current v2 wiring** and were recommended for deletion:
`services/gateway/router.py`, `services/ai-worker/`, `services/rag-service/`
(hyphen), `services/pdf-service/` (hyphen), `services/stt/` (hyphen),
`services/vision-service/`. See the running deletion list maintained
alongside this doc for the current status of each.

---

## 8. Vendor consolidation: OpenAI removed, Sarvam-only + free local fallback

**What changed:** every OpenAI call point has been removed — the old
`whisper-1` STT tier, `gpt-4o-mini` text tier, and `gpt-4o-mini` vision tier
are all gone. Every agent (Ledger, Pricing, Market, Government Schemes,
Vision, Advertisement, Negotiation, Speech) now has exactly **two** tiers:

1. **Sarvam** (paid, primary) — `sarvam-30b` for standard-tier text tasks,
   `sarvam-105b` for advanced tasks (ads, negotiation, pricing phrasing),
   `sarvam-vision` for product photo identification, `saaras:v3` for STT.
2. **Local Ollama** (free, self-hosted) — the *only* fallback. `faster-whisper`
   remains the dedicated STT fallback specifically (it doesn't run through
   the general Ollama chat/vision path).

**Why this matters more than it sounds:** previously, OpenAI functioned as
an implicit "this will basically always eventually work" third tier under
Sarvam-and-local. That tier is gone. If `SARVAM_API_KEY` is unset/failing
**and** `USE_LOCAL_MODELS=false`, every text/vision agent now raises
`ModelUnavailableError` immediately — there is no other paid vendor to fall
through to. In practice this means `USE_LOCAL_MODELS=true` plus a reachable
Ollama box is no longer a nice-to-have cost optimization; it is the
production uptime story. See `docs/COST.md` for the updated cascade table
and `scripts/check_env.py`, which now warns explicitly if neither tier is
configured.

**Open verification item:** Sarvam Vision's product-photo capability has not
been confirmed against current Sarvam API docs — Sarvam Vision has
historically been positioned as document/OCR intelligence, not general
product-photo understanding. `catalog_node.py`/`vision_router.py` now route
through `route_vision_completion`, which tries Sarvam Vision first and the
local Ollama vision model (`qwen2-vl`) second. **Verify Sarvam Vision's
actual scope before relying on it as the production primary** — if it turns
out to be document-scoped only, set `USE_LOCAL_MODELS=true` and treat the
Ollama tier as the real primary for this agent specifically.

**New agent added:** Pricing Recommendation (`services/orchestrator/nodes/pricing_node.py`).
Deterministic core (cost + margin + market-floor math against the seller's
own `production_cost`/`minimum_price`/`preferred_margin`, stored in the new
`seller_profiles` table) — Sarvam is used only to phrase the explanation in
warm Bengali, never to generate the price itself, matching the same
"deterministic core, LLM for language only" pattern already used in
`grounding_verifier.py` and `aggregator.py::classify_trend`.

**Not yet built:** a Negotiation agent. If built, the same guard-rail
pattern applies even more strictly: the LLM should generate persuasive
Bengali phrasing only, and should **never** see or reason about
`seller_profiles.minimum_price` directly — any flow that would confirm a
sale below the stored floor must be rejected in code, not merely
discouraged in the prompt.
