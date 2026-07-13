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

### 6. Red-team pass #3 and fixes (see `docs/red-team-agents-v2.md` for full detail)
Every finding below was reproduced against the actual code with a runnable
PoC before being fixed, and re-verified against the fix afterward —
including a real `pytest` run (26/26 passing) and a second bypass round that
caught a gap in my own first fix (spelled-out number words) before shipping.

- **CRIT-1 (fixed):** the negotiation agent's original "safety net" —
  scanning LLM output for `₹`/`টাকা` patterns — was a bypassable blocklist.
  Proven to miss bare digits, the Bengali Taka sign (৳), romanized "taka",
  and spelled-out number words. **Redesigned structurally**: the LLM
  (`negotiation_node.py`) is no longer asked to write a price at all, only
  an optional digit-and-number-word-free justification sentence
  (`_mentions_a_number`); the actual quoted amount is always interpolated
  by code from an already-floor-safe, deterministically computed value.
- **HIGH-1 (fixed):** a WhatsApp message containing a ~400-digit number
  parsed to `float('inf')` via `_extract_amount`, which unconditionally
  satisfied `offer >= floor` for any floor. `_extract_amount` now rejects
  non-finite values and anything above `MAX_REASONABLE_OFFER` (₹5,00,000,
  matching `ledger_confirm_node`'s existing pattern).
- **MED-1 (fixed):** `pricing_node._recommend` had no bounds on
  `cost`/`margin`/`min_price` — a negative or zero `production_cost` with
  no `minimum_price` set collapsed the floor to ₹0, which `negotiation_node`
  would then treat as "accept anything." Not reachable via chat today (no
  orchestrator node writes `seller_profiles` yet), but fixed now since a
  future price-setting flow will make it directly reachable. Inputs are now
  clamped non-negative, and every caller explicitly refuses to proceed when
  `floor_price <= 0`.
- **MED-2 (fixed):** `flux_poster_client.py` downloaded its result image
  with no size cap and no scheme check — same vulnerability class as your
  own `red-team.md` CRIT-2 (PDF SSRF), just against a vendor API response
  instead of raw user input. Now a size-capped streaming download,
  https-only.
- **LOW-1 (fixed):** the Flux Pro prompt embedded unsanitized,
  unbounded-length AI-generated text (itself derived from a user-submitted
  photo via the vision model). Now truncated and control-character-stripped
  before use, mirroring `pdf_service`'s existing `_clean()` pattern.
- **LOW-2 (fixed):** no overall wall-clock budget on Flux polling — a
  slow-but-not-failing endpoint could tie up a Celery worker slot for
  minutes. Now wrapped in a hard 60s outer `asyncio.wait_for` ceiling.

### 7. Local Bengali calendar + local product taxonomy
- `shared/i18n/bengali_calendar.py` — **new file**. Centralizes the
  Gregorian-months-in-Bengali-script dict that was previously duplicated
  identically in `pdf_service/generator.py` and `ledger_report_node.py`
  (`GREGORIAN_MONTHS_BENGALI`, kept as the authoritative date everywhere —
  bank/government paperwork stays Gregorian). Adds a real Bangla calendar
  (Bangabda) conversion, `gregorian_to_bangla_approx`, shown as a clearly
  labeled secondary "(আনুমানিক)" / "approximate" reference in the PDF
  report and WhatsApp report caption — not a replacement for the Gregorian
  date. Verified structurally valid across a 4-year span including a leap
  year (`tests/unit/test_bengali_calendar.py`, 7 tests); the exact
  day-boundary precision is explicitly flagged as unverified against a
  specific West Bengal panjika (see the module's own verification note,
  same pattern as the Sarvam Vision / Flux Pro flags).
- `shared/catalog/local_products.py` — **new file**. A real West Bengal SHG
  product taxonomy (papad, pickle, Kantha embroidery, poultry, vegetables,
  jute handicraft, terracotta, mushroom, honey, mustard oil, muri, batik,
  tailoring, candle/soap) drawn directly from the personas and trade list
  already in `docs/product.md` and `docs/archive/engineering/llm-guide.md`
  — not an invented generic catalog. Covered by
  `tests/unit/test_local_products.py` (13 tests: data integrity + both
  matching helpers).
- `services/vision_service/vision_router.py` — price-range suggestions now
  try a specific local-product match first (e.g. "kantha saree" -> ₹500–
  ₹2000) before falling back to the old 5-bucket broad category range,
  both now sourced from the new shared module instead of a hardcoded dict
  duplicated in this file.
- `services/orchestrator/nodes/catalog_node.py` — `_CATEGORY_KEYWORDS` (used
  for the market-trend note) is now generated from the local product list
  instead of a separately hand-maintained dict that only covered 4
  categories with 2–4 keywords each. Poster titles now use the localized
  Bengali product name (`_product_label_bengali`) when a local match is
  found, instead of always falling back to the raw English vision output
  or a generic "পণ্য".

## Still open / needs your decision

1. **Verify Sarvam Vision's actual scope** (product photos vs. document/OCR-only) against current Sarvam docs before trusting it as the catalog-vision primary — see the flag in `model_router.py`, `sarvam_client.py`, and `architecture.md` §8.
2. **Verify Flux Pro's endpoint/payload shape** against your account's current docs — `flux_poster_client.py`'s request/response format is a best-effort implementation, not confirmed live. Any mismatch degrades safely to the Pillow tier.
3. **Enable `USE_LOCAL_MODELS=true`** before real pilot traffic — it's no longer optional in practice now that OpenAI isn't there as a backstop.
4. **`migrations/0002_hybrid_search.sql`** (Scheme RAG) is still undeployable — the table it alters is never created. Not touched by this update; see `DELETE_LIST.md` section C.
5. **Negotiation agent's offer extraction** is a single-amount regex — a message with multiple numbers only picks up the first one. Fine for single-item bargaining; revisit if multi-item negotiation becomes common.
6. **When you eventually build a chat-driven flow that writes to `seller_profiles`** (e.g. "set my price" via voice, matching the ledger pattern), reuse `ledger_confirm_node._validate_amount`'s validation approach for `production_cost`/`minimum_price` — the MED-1 fix in `_recommend` is defense-in-depth, not a substitute for validating at the point of entry too.
7. **The Bangla calendar conversion's exact day-boundary precision is unverified** against a specific West Bengal panjika — see `shared/i18n/bengali_calendar.py`'s own note. It's used only as a secondary, clearly-labeled "approximate" display; nothing legal/financial depends on it. If a pilot user flags the displayed Bangla month as wrong for their local panjika, that's expected variance, not a bug to chase precisely.
8. **`shared/catalog/local_products.py` is a starting list (14 products), not exhaustive** — extend it as real pilot users report products it doesn't recognize; the matching helpers (`find_local_product_by_slug`/`_by_bengali_text`) already fail safe (return `None`, fall back to broad category ranges) for anything not yet in the list.
