# Cost design — the cascade, and why

## The cascade, per agent (OpenAI removed — see architecture.md §8)

| Agent / call type | Paid tier | Free fallback (final — no third tier exists) |
|---|---|---|
| Ledger extraction, corrections, market phrasing, pricing phrasing, off-topic chat | **Sarvam-30B** | Local Ollama (Qwen2.5-7B) |
| Advertisement captions, Negotiation | **Sarvam-105B** | Local Ollama |
| Government Schemes (if re-enabled) | **Sarvam-30B** | Local Ollama |
| Product photo identification (Vision) | **Sarvam Vision** | Local Ollama vision (`qwen2-vl`) |
| Speech-to-text | **Saaras V3** | Self-hosted `faster-whisper` (free, always available) |
| Bengali↔English translation / Banglish normalization | **Sarvam** `/translate` | Your self-hosted `sarvam-translate` box, if configured → else local Ollama |
| Poster generation | **Flux Pro** (optional, real API integration in `flux_poster_client.py`) | Pillow composite (`poster_composer.py`, free, always works — this is the tier that actually ships if `FLUX_API_KEY` is blank or Flux fails for any reason) |

Each cheap-vs-fallback decision is gated by the tier's own self-reported
confidence — same mechanism regardless of which tier produced it, see
`_parse_self_reported_confidence` in `model_router.py`.

## Why this shape, specifically

- **Sarvam is now the sole paid vendor.** There is no OpenAI tier under or
  above it anymore. This simplifies the vendor surface (one dashboard, one
  spend cap to set) but also means **local Ollama is no longer optional in
  practice** — with OpenAI gone, it's the only thing between a Sarvam outage
  and total silence for every text/vision agent. Strongly recommended to
  enable `USE_LOCAL_MODELS=true` before any real pilot traffic.
- **Sarvam Vision for product photos, with an open verification item.**
  Sarvam Vision has historically been positioned as document/OCR
  intelligence rather than general product-photo understanding — confirm
  against current Sarvam docs before trusting it as the catalog-vision
  primary in production. The local Ollama vision fallback (`qwen2-vl`)
  exists specifically to cover this uncertainty.
- **A cheap heuristic gates the translation call**, not a model call. Most
  voice notes are already clean Bengali; running every single one through
  `/translate` "just in case" would be the single biggest avoidable cost in
  this design. `_looks_code_mixed()` in `ledger_node.py` is a character-ratio
  check, not an API call — translation only fires when the text actually
  looks Banglish/code-mixed.
- **Pricing recommendations are never LLM-generated numbers.** The price
  floor/recommendation math in `pricing_node.py` is deterministic Python —
  Sarvam-105B is used only to write a warm Bengali explanation of a number
  that was already computed. Same pattern as the market trend classifier.
- **The off-topic conversation node only fires off the happy path.** It
  doesn't add cost to normal ledger/catalog/market/pricing usage — only to
  messages that already failed intent classification.

## What to actually watch

- Sarvam pricing tiers (Starter/Pro/Business/Enterprise) and exact per-token
  rates change — check `sarvam.ai`'s current pricing page rather than
  trusting a number here that may be stale by the time you read this.
- Set a spend cap on the Sarvam dashboard — the app-level per-number rate
  limit (30 msgs/hour) is one safety net; a platform-side hard cap is a
  second, independent one. With OpenAI removed, Sarvam is your only paid
  exposure, so this cap matters more than it used to.
- If you enable Flux Pro, set a separate spend cap there too — per-image
  pricing on a poster-generation feature can scale unpredictably with
  catalog usage.
- If you want a rough sense of where spend concentrates: log `model_used`
  from every `route_completion` / `route_translation` / `route_vision_completion`
  result (already returned in the result dict, just not persisted yet) for
  a day of real traffic, and count how often each tier actually gets used —
  a high `ollama-local` rate means Sarvam is failing more than expected and
  worth investigating, not just a cost win.
