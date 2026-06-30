# Kotha-Khata v2 — Architecture Decisions

This document records what changed from the original plan (`docs/PRD.md`, `docs/TRD.md`,
`docs/ROADMAP.md` in the v1 repo) and **why**, based on a review of 2026 production
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
this exact reason — see `docs/research/agent_frameworks.md`).

Celery is **kept** only as the execution substrate (so a slow node doesn't block the
20s WhatsApp webhook ack) — LangGraph runs *inside* a Celery task, not instead of it.

## 2. Voice stack: Bhashini-primary → three-tier provider cascade, Sarvam-primary

**v1 problem:** TRD specified Bhashini as the primary STT with self-hosted Whisper as
fallback. As of 2026, independent Bengali STT benchmarks show Sarvam AI's ASR is
measurably more accurate and lower-latency on regional/dialectal Bengali than
Bhashini, while Bhashini's free tier is excellent for cost control but not built for
latency-sensitive production traffic.

**v2 decision:** `services/voice-gateway/provider_cascade.py` tries, in order:

1. **Sarvam AI** (`saarika` STT / `bulbul` TTS) — primary, paid, best accuracy/latency.
2. **Bhashini** — fallback on Sarvam error/timeout/budget-cap, free, GoI-backed.
3. **Self-hosted fine-tuned `faster-whisper`** — final fallback, zero marginal cost,
   works offline if the GPU box is reachable but the internet/API providers are not.

This keeps the original's "zero marginal cost at scale" end-state (tier 3 absorbs
volume once fine-tuned and trained on pilot data) while fixing the day-1 quality gap
of defaulting to a free-tier API for a literacy-sensitive, voice-first product.

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

## 4. LLM usage: all-Claude or all-self-hosted → cascaded by task criticality

**v1 problem:** The roadmap's "phased migration" implied a binary switch — pay for
Claude everywhere during MVP, then flip to 100% self-hosted Qwen post-pilot. That
either overpays during MVP or silently degrades grounding quality on the
highest-stakes output (scheme eligibility verdicts) once migrated.

**v2 decision:** `services/orchestrator/model_router.py` routes by task:
- **Safety-critical** (scheme RAG generation + grounding verification, eligibility
  verdicts): always Claude Sonnet — wrong scheme info has real consequences.
- **Routine/high-volume** (ledger NER, meeting-minutes extraction, intent
  classification): self-hosted fine-tuned Qwen2.5-7B via Ollama — cheap, fast, and
  the gap closes with domain fine-tuning per the original's own quality table.
- A confidence threshold escalates a "routine" call to Claude if the local model's
  self-reported confidence is low, instead of silently shipping a bad extraction.

## 5. RAG hallucination prevention: a hardcoded flag → a real two-pass verifier

**v1 problem:** `pipeline.py` returned `"hallucination_check_passed": True`
unconditionally. There was no actual verification step.

**v2 decision:** `services/rag-service/grounding_verifier.py` implements the
2026-standard two-pass pattern:
1. **Assertion extraction** — pull every number, date, scheme name, and amount out
   of the generated Bengali answer (regex + light NER).
2. **Grounding check** — for each assertion, verify it is actually present in the
   retrieved chunks (not just topically similar). Any ungrounded assertion forces a
   rewrite-or-refuse, never a silent pass-through.

Retrieval itself moves from vector-only to **hybrid**: Postgres full-text search
(`tsvector`/`ts_rank`, zero extra infra) fused with pgvector cosine similarity via
reciprocal rank fusion — this was *described* in the original TRD's pipeline diagram
but never actually implemented in `pipeline.py`; v2 implements it.

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
present in the combined context, just attached to the wrong scheme. This is
exactly the gap flagged in `docs/INTERNSHIP_GUIDE.md`'s Day 4–5 task and in
`docs/research/agent_frameworks.md`'s note on "citation-shaped hallucinations."

**Fix:** grounding is now checked per-chunk, and whenever the answer names a
scheme near an assertion (using a small Bengali/Latin alias table,
`SCHEME_NAME_ALIASES`), that assertion must be found within a chunk
belonging to *that specific* scheme. Assertions with no identifiable nearby
scheme mention keep the old, more lenient behaviour (grounded if found
anywhere in the retrieved set) so short, scheme-less answers don't start
failing spuriously.

Verified with a reproduction: feeding the old (pre-fix) logic the exact
"Lakshmir Bhandar claims JAAGO's ₹2500" case returns `all_grounded: True`
(the bug); the new logic correctly returns `False`. Nine tests now cover
this in `tests/unit/test_grounding_verifier.py`, including a "swapped
amounts across two schemes" case and a multi-scheme comparison answer that
should still pass when correctly attributed.

**Known limitation, left for a follow-up PR:** scheme-name detection is a
fixed lookback-window alias match, not a real coreference/NER pass. A
sentence structured so the scheme name appears *after* the amount
("₹2500 আপনি লক্ষ্মীর ভান্ডার থেকে পাবেন") would not be caught by the
current backward-only lookback. If this turns out to be a common generation
pattern in practice (check via `scripts/audit_rag.py`'s weekly human audit),
extend `_nearby_scheme` to look both directions within the sentence
boundary, not just backward.

### 7.2 Dead-code audit: pre-LangGraph v1 remnants still in the tree

While tracing the message-handling path end to end (the Day 3 exercise), the
following v1-era files/directories were found to be **unreferenced by
anything in the current v2 wiring** (`docker-compose.yml`, the Dockerfiles,
and `services/orchestrator/graph.py`/`celery_entrypoint.py`), and should be
deleted rather than maintained going forward:

| Path | Why it's dead |
|---|---|
| `services/gateway/router.py` | Superseded by `services/orchestrator/nodes/intent_router.py` per `graph.py`'s own docstring. Also **currently broken**: it does `from services.ai_worker import tasks` (underscore) but the only such package on disk is `services/ai-worker/` (hyphen, and contains only an empty `__init__.py`) — this import would raise `ModuleNotFoundError` if anything still called it. |
| `services/ai-worker/` | Empty stub; superseded by orchestrator nodes (see §1 above). |
| `services/rag-service/` (hyphen) | Older copy of `services/rag_service/pipeline.py` — vector-only retrieval, no hybrid search, no real grounding check (`"hallucination_check_passed": True` hardcoded). The actively-used module is `services/rag_service/` (underscore), imported by `services/orchestrator/nodes/scheme_rag_node.py`. |
| `services/pdf-service/` (hyphen) | Duplicate of `services/pdf_service/` (underscore). `docker-compose.yml` and `services/pdf_service/Dockerfile` only reference the underscore version. |
| `services/stt-service/` (hyphen) | Pre-cascade standalone Whisper service (`whisper_engine.py`, its own `Dockerfile.gpu`). Superseded by the 3-tier cascade in `services/voice_gateway/provider_cascade.py`. Not in `docker-compose.yml`. |
| `services/vision-service/` | Empty stub (`__init__.py` only); no vision node exists yet in the graph — tracked as an open `_route_after_intent()` TODO in `graph.py`, not implemented here. |

None of this affects runtime behavior today (nothing imports the hyphenated
packages), but it's confusing for anyone reading the repo fresh — exactly the
kind of thing that costs a new intern a wasted hour during the Day 3 trace
exercise. Recommended next step: delete the hyphenated/dead directories in a
dedicated cleanup PR (no logic changes, just `git rm -r`), separate from any
feature work, so the diff is trivial to review.
