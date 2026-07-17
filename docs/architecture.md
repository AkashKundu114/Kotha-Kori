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

> **Update, §10.3 below:** as of Pass 3, ledger *confirmation* (not just intake) also
> has a Flow option — `ledger_confirm_flow.json` — extending this same v2 decision to
> the one remaining plain-text confirm/correct loop that predates it.

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

> **Update, §10.4 below:** Pass 4 generalizes this exact "never trust the model to
> state a sensitive value, verify or structurally prevent it" principle to a second
> surface — `cross_verify.py`, an independent second-model-call check applied to
> pricing-chat outbound messages, not just RAG answers.

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

**Update — now built:** the Negotiation agent and a real Flux Pro poster
tier are both implemented. See §9 below.

## 9. Negotiation agent (built) + Flux Pro poster tier (built)

### 9.1 Negotiation agent — `services/orchestrator/nodes/negotiation_node.py`

Follows the guard-rail pattern flagged as a requirement when this agent was
still just a design note: the LLM (Sarvam-105B) is used **only** to phrase
responses in warm Bengali. It never decides whether an offer is accepted,
and it never generates the counter-offer number itself. Three independent,
code-level enforcement points, not prompt instructions:

1. **Accept/reject is a plain Python comparison** (`offer >= floor` in
   `_evaluate_offer`) against a floor computed by the same deterministic
   `_recommend()` function the Pricing agent uses (`pricing_node.py`).
2. **The counter-offer amount is computed in code** (`_compute_counter_offer`,
   a pure function covered by `tests/unit/test_negotiation_node.py`) using
   `max(floor, ...)`, which makes a below-floor result structurally
   impossible, not just unlikely.
3. **A post-generation safety net** (`_contains_amount_below`) scans every
   LLM-generated response for any rupee amount. If the model ever
   hallucinates a lower number, the entire generated message is discarded
   for a deterministic Bengali fallback line — same philosophy as
   `grounding_verifier.py`, applied to a financial floor instead of a
   citation claim.

Capped at `MAX_NEGOTIATION_TURNS = 4`; past that, the agent deterministically
holds firm at the floor price and ends the negotiation.

> **Update, §10.4 below:** Pass 4 wires this agent to
> `shared/knowledge/negotiation_playbook.py` — the *choice* of negotiation
> tactic (anchor / reciprocity / justify-value / graceful walk-away) is now
> made deterministically from the offer-to-floor ratio and turn number,
> with the LLM only phrasing whichever tactic was chosen. Previously the
> LLM picked its own framing implicitly; now the strategy itself is
> code-selected too.

### 9.2 Flux Pro poster tier — `services/vision_service/flux_poster_client.py`

Real async submit -> poll -> download integration, wired into
`poster_composer.py`'s new `generate_poster()` as the optional first tier.
The existing Pillow `compose_poster()` remains the permanent free fallback.
`catalog_node.py` now calls `generate_poster()` and tags the delivered
poster's trace/S3 key with which tier actually produced it.

**Open verification item:** the endpoint paths and payload shape in
`flux_poster_client.py` are a best-effort implementation against Flux
Pro's documented pattern, not verified against live docs. Any mismatch
raises `FluxUnavailableError` and falls through to Pillow automatically —
it never ships a broken image silently. Verify before trusting Flux as
reliable in production.

---

## 10. Addendum — Passes 1–6: shared cultural/market knowledge, dignity rules,
## Flow-verified ledger writes, friend-style pricing, negotiation tactics, cross-verification

This section, like §7 above, is appended rather than rewriting history.
It covers six incremental passes, each documented in its own
`CHANGELOG_v4`–`v9` file at the repo root — this section is the
architectural summary; those files carry the turn-by-turn detail (what
changed, what's still open, what's honestly unverified) for anyone tracing
a specific decision.

### 10.1 Shared knowledge base — one source of cultural/seasonal context, not N copies

**Problem this solves:** festival timing, seasonal price patterns, and
family-occasion demand signals are relevant to at least four agents
(pricing, negotiation, catalog, market predictor). Without a shared source,
each node either duplicates this knowledge (drifting out of sync, the same
failure mode `bengali_calendar.py`'s `GREGORIAN_MONTHS_BENGALI` already had
before it was centralized) or simply doesn't have it.

**Decision:** `shared/knowledge/context.py` is the single source. Its one
public entry point, `get_context_for_agents(month, block, district)`,
returns statewide festivals (`FESTIVALS`), district-specific melas
(`DISTRICT_MELAS`, Pass 6), and generic seasonal weather/price notes
(`SEASONAL_PATTERNS`) — all as plain data, never phrased Bengali prose, so
every calling node still routes final phrasing through `model_router.py`
per the existing "deterministic core, LLM for language only" split.
`shared/knowledge/life_events.py`... — actually life-cycle occasions live
in the same `context.py` module (`LIFE_EVENTS`, `life_events_by_community`)
rather than a separate file, since they're read by the same callers via the
same import.

**What's real vs. approximate, stated once here and per-entry in the file
itself:** every festival/occasion/mela entry carries a `source_note` citing
where it came from — Wikipedia articles for Hindu and Muslim Bengali
wedding rites, a purohit reference site for pujas, named tourism/heritage
sources for the district melas, and an explicit, weaker flag on the three
Christian Bengali entries (one non-academic blog source plus two
general-Christian-practice entries with no Bengal-specific citation). Dates
are typical-month approximations, not a real per-year lunar/panchang
calendar — `sources_todo` at the bottom of the file lists exactly what a
live calendar API integration would need to replace this with.

**What this is not:** a "100+ verified entries" catalog. As of Pass 6 it's
~14 life-cycle occasions, 11 statewide festivals, 5 district melas. Getting
further needs either a real scraping pipeline against a licensed
panchang/government data source, or continued manual research passes —
both are real follow-up work, not something to fabricate to hit a number.

### 10.2 Dignity guidelines — one shared tone contract, and an explicit no on caste/rashi

`shared/knowledge/dignity_guidelines.py` centralizes the tone rules now
prepended to every Bengali-facing conversational system prompt (ledger
confirmation phrasing, off-topic conversation, catalog captions, market
advice, pricing explanations, negotiation reasoning, the friend-style
pricing chat). Rule of thumb encoded there: never imply the user doesn't
understand something, take blame for misunderstanding onto the assistant
rather than the user, address the user as an equal-status entrepreneur
rather than a charity recipient.

The same module documents, explicitly, why **caste, gotro/gon, and rashi
(zodiac) are not tracked anywhere in this codebase** despite being
requested: none of the product's actual features need them, and adding
caste specifically as a stored/personalized attribute would create a
discrimination-enabling asset for a population that can't easily contest
its misuse — the wrong trade for a financial-inclusion tool. This is a
product-safety decision, not an oversight, and is recorded here so it
doesn't get silently re-proposed later without the reasoning attached.

### 10.3 WhatsApp Flow verification before permanent ledger writes

**Problem this solves:** the original ledger confirmation loop
(`ledger_confirm_node.py`) asks the user to type হ্যাঁ/না — itself a source
of the exact typo/mishearing risk the confirmation step exists to catch in
the first place.

**Decision:** `services/gateway/whatsapp_flows/ledger_confirm_flow.json`
adds a tap-to-confirm form (✅ ঠিক আছে / ✏️ সংশোধন করব / ❌ বাতিল করুন) as a
second front door onto the *same* save logic.
`services/orchestrator/nodes/ledger_confirm_flow_node.py` consumes the tap;
`shared/whatsapp/sender.py:send_flow()` actually sends it; `graph.py`
routes an interactive reply to the Flow-aware node specifically when its
payload contains `confirmation_choice`, falling back to the original
text-based node otherwise. Critically: **there is still exactly one code
path that ever writes to `ledger_entries`** — both confirmation routes call
the same `_save()` in `ledger_confirm_node.py`. The Flow is a second lock
pick, not a second lock. Configuration is optional
(`WA_LEDGER_CONFIRM_FLOW_ID`); unset, behavior is unchanged from before
this pass.

**Open verification item**, same honesty category as Sarvam Vision/Flux Pro
above: `send_flow()`'s payload shape (a static "flow_action: navigate"
message, no data-exchange endpoint) is a best-effort implementation of
Meta's documented format, not verified against a live WABA send in this
codebase's development so far.

### 10.4 Friend-style pricing chat, negotiation tactics, and cross-agent verification

**`services/orchestrator/nodes/price_chat_node.py`** — a SELLER-facing
conversational pricing negotiation (distinct from `negotiation_node.py`,
which handles a *customer's* counter-offers after a poster is already
live), run before `catalog_node.py` composes a poster. Follows the same
guard-rail shape as the existing Negotiation agent: the floor is the same
`pricing_node._recommend()` floor, the LLM never states a number, and the
node hard-stops at the floor rather than silently capping a seller's
request below it — instead explaining why, using the seller's own
previously-stated `production_cost`/`minimum_price`.

**`shared/knowledge/negotiation_playbook.py`** — standard, publicly
documented negotiation concepts (anchoring, BATNA, reciprocity, silence,
bundling, value-justification, graceful walk-away) as strategy labels with
short Bengali coaching lines, never as a source of numbers. `choose_tactic`
deterministically picks a strategy from the turn number and offer/floor
ratio; `negotiation_node.py` folds the chosen tactic's coaching line into
the LLM's reason-generation *prompt* (not its system prompt) as of Pass 4.

**`services/orchestrator/nodes/cross_verify.py`** — the person's request
that "one agent's output should be verified... by another agent" applied
concretely and boundedly: an independent second model call
(`verify_dignity`) checks a fully-composed outbound message against the
dignity rules, combined with a fully deterministic numeric-integrity check
(`check_numeric_integrity`) that every ₹ figure in the draft matches a
code-computed value the caller actually supplied. `price_chat_node.py`
runs every LLM-touched outbound message through this before sending, and
falls back to a deterministic, code-only line if verification fails or is
itself unavailable — never sends an unverified draft. This is explicitly
*not* a full N-agent debate/consensus architecture (that's a real,
separate scope decision involving latency and cost tradeoffs); it is one
bounded, honest second-opinion pass on the highest-stakes outbound
messages.

### 10.5 What's still open after Pass 6

- Live testing against a real WABA (Flow sends, Flow receives, the whole
  turn) has not happened in this codebase's development so far — see the
  open-verification flags in §10.3 above and in `send_flow()`'s own
  docstring.
- `negotiation_node.py`'s `is_repeat_customer` signal is hardcoded to
  `False` — there's no data source tracking customer identity across
  negotiations, and building one is a real privacy/consent scope decision,
  not a code change to make silently.
- Christian Bengali life-cycle sourcing (§10.1) is genuinely weaker than
  the Hindu/Muslim entries and should be strengthened before being treated
  as equally reliable.
- No live festival/panchang calendar API is wired in — `month_hint`
  approximations only.
