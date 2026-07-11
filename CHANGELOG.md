# Changelog — OpenAI removal + Pricing agent + cleanup

## How to apply this package

These files mirror the exact paths in your repo. Copy each one over the
corresponding path in your checkout (or `cp -r` this whole tree into your
repo root and let it overwrite), review the diff, then run the deletions in
`DELETE_LIST.md`.

```bash
cp -r kotha-khata-updates/* /path/to/your/repo/
cd /path/to/your/repo
git diff                 # review before committing
# then work through DELETE_LIST.md
```

## What changed

### 1. OpenAI removed entirely
- `shared/config/settings.py` — `openai_api_key`/`openai_model`/`openai_vision_model` removed; added `sarvam_advanced_model`, `sarvam_vision_model`, `saaras_model`, `ollama_vision_model`, `flux_api_key`/`flux_base_url`.
- `services/orchestrator/model_router.py` — rewritten. Every `_call_openai*` function removed. Two-tier cascade only: Sarvam → local Ollama. New `AgentTier` enum (`STANDARD` = sarvam-30b, `ADVANCED` = sarvam-105b). `route_vision_completion` now goes Sarvam Vision → Ollama vision, no OpenAI vision fallback.
- `services/translation_service/sarvam_client.py` — `chat_completion` takes an optional `model` param (for the advanced tier); new `vision_completion` function.
- `services/voice_gateway/providers/saaras_provider.py` — **new file**, replaces `openai_stt_provider.py`.
- `services/voice_gateway/provider_cascade.py` — Saaras V3 primary, `faster-whisper` free fallback (unchanged).
- `requirements.txt` — `openai==1.51.0` removed as a top-level pin (still usable as an optional lazy import for the self-hosted-vLLM wire protocol, see comment in the file).
- `.env.example`, `scripts/check_env.py`, `tests/conftest.py`, `SETUP.md`, `README.md`, `docs/COST.md`, `docs/architecture.md` (new §8) — all updated to match.

### 2. New: Pricing Recommendation Agent
- `services/orchestrator/nodes/pricing_node.py` — **new file**. Deterministic cost/margin/floor calculation (`_recommend`, covered by `tests/unit/test_pricing_node.py`), Sarvam-105B used only for phrasing the explanation.
- `shared/db/models.py` — new `SellerProfile` model.
- `migrations/0004_seller_profile.sql` — **new file**, additive migration for `seller_profiles` table + `market_prices.demand_score` column.
- `services/orchestrator/state.py` — `"PRICING"` added to the `Feature` literal.
- `services/orchestrator/nodes/intent_router.py` — `PRICING_KEYWORDS` + routing branch added.
- `services/orchestrator/graph.py` — `pricing` node wired in.

### 3. Cleanup
- See `DELETE_LIST.md` for the full breakdown (confirmed-dead vs. judgment-call vs. do-not-delete).

### 4. New: Negotiation Agent (built, not just designed)
- `services/orchestrator/nodes/negotiation_node.py` — **new file**. Accept/reject is a plain code comparison against the same deterministic floor `pricing_node.py` computes. The counter-offer amount is computed by a pure function (`_compute_counter_offer`, `max(floor, ...)` — structurally cannot go below floor). Every LLM-generated response (accept phrasing and counter phrasing, both Sarvam-105B) is scanned afterward by `_contains_amount_below` and discarded in favor of a deterministic fallback line if it ever quotes below the floor. Covered by `tests/unit/test_negotiation_node.py`.
- `services/orchestrator/state.py` — `"NEGOTIATION"` added to `Feature`, new `PendingNegotiation` TypedDict, `pending_negotiation`/`awaiting_negotiation` fields.
- `services/orchestrator/nodes/intent_router.py` — `NEGOTIATION_KEYWORDS` + routing branch, checked before `PRICING_KEYWORDS`.
- `services/orchestrator/graph.py` — `negotiation` node wired in, including the mid-negotiation direct-route (same pattern as `ledger_confirm`).

### 5. New: Flux Pro poster tier (real API integration, not a config placeholder)
- `services/vision_service/flux_poster_client.py` — **new file**. Real async submit → poll-by-id → download-result-URL client against Flux Pro's documented pattern. Raises `FluxUnavailableError` on any failure (missing key, HTTP error, bad shape, moderation rejection, polling timeout).
- `services/vision_service/poster_composer.py` — updated. Existing `compose_poster()` (Pillow) is **unchanged** and remains the permanent free fallback. New async `generate_poster()` tries Flux Pro first (only if `FLUX_API_KEY` is set), falls through to `compose_poster()` on any failure or if unconfigured.
- `services/orchestrator/nodes/catalog_node.py` — updated to call `generate_poster()` instead of calling `compose_poster()` directly; traces/S3-keys now record which tier (`flux-pro` / `pillow` / `none`) actually produced the delivered poster.
- Covered by `tests/unit/test_flux_poster_fallback.py`.

## Still open / needs your decision

1. **Verify Sarvam Vision's actual scope** (product photos vs. document/OCR-only) against current Sarvam docs before trusting it as the catalog-vision primary — see the flag in `model_router.py`, `sarvam_client.py`, and `architecture.md` §8.
2. **Verify Flux Pro's endpoint/payload shape** against your account's current docs — `flux_poster_client.py`'s request/response format is a best-effort implementation, not confirmed live. Any mismatch degrades safely to the Pillow tier, it doesn't break the flow.
3. **Enable `USE_LOCAL_MODELS=true`** before real pilot traffic — it's no longer optional in practice now that OpenAI isn't there as a backstop.
4. **`migrations/0002_hybrid_search.sql`** (Scheme RAG) is still undeployable — the table it alters is never created. Not touched by this update; see `DELETE_LIST.md` section C.
5. **Negotiation agent's offer extraction** is a single-amount regex (same limitation as `grounding_verifier.py`'s assertion extraction) — a message with multiple numbers only picks up the first one. Fine for single-item bargaining; revisit if multi-item negotiation becomes common.
