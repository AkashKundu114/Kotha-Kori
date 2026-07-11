# Cost design — the cascade, and why

## The cascade, per call type

| Call type | 1st tier | 2nd tier (optional) | Final fallback |
|---|---|---|---|
| Ledger extraction, corrections, market phrasing, captions, off-topic chat | **Sarvam** (`sarvam-30b`) | Self-hosted Ollama, if enabled | OpenAI (`gpt-4o-mini`) |
| Bengali↔English translation / Banglish normalization | **Sarvam** `/translate` | Your self-hosted `sarvam-translate` box, if configured | OpenAI (asked to translate via a plain prompt) |
| Product photo understanding (vision) | — | — | **OpenAI only** (Sarvam has no comparable vision model) |
| Speech-to-text | **OpenAI Whisper API** | — | Self-hosted `faster-whisper` (free, always available) |

Each cheap tier's own self-reported confidence gates whether its output is
trusted or the next tier is tried, exactly the same mechanism regardless of
which tier produced it — see `_parse_self_reported_confidence` in
`model_router.py`.

## Why this shape, specifically

- **Sarvam first for text, not vision.** Sarvam is a genuinely strong,
  cheap, Bengali-native model for exactly the structured-extraction and
  captioning workload this bot does constantly. It has no product-photo
  vision capability at all, so paying to call it for images would be pure
  waste — OpenAI vision is not optional, it's the only tool that does the
  job.
- **A cheap heuristic gates the translation call**, not a model call. Most
  voice notes are already clean Bengali; running every single one through
  `/translate` "just in case" would be the single biggest avoidable cost in
  this design. `_looks_code_mixed()` in `ledger_node.py` is a character-ratio
  check, not an API call — translation only fires when the text actually
  looks Banglish/code-mixed.
- **The off-topic conversation node only fires off the happy path.** It
  doesn't add cost to normal ledger/catalog/market usage — only to messages
  that already failed intent classification.
- **Vision analysis and caption generation are two separate calls, not one
  combined one**, because they have different cost/quality tradeoffs:
  vision needs OpenAI's actual image understanding, but turning that
  structured output into warm Bengali prose is exactly the kind of task
  Sarvam is both cheap and good at.

## What to actually watch

- Sarvam pricing tiers (Starter/Pro/Business/Enterprise) and exact per-token
  rates change — check `sarvam.ai`'s current pricing page rather than
  trusting a number here that may be stale by the time you read this.
- Set a spend cap on **both** the OpenAI and Sarvam dashboards — the app-level
  per-number rate limit (30 msgs/hour) is one safety net; a platform-side
  hard cap on each vendor is a second, independent one.
- If you want a rough sense of where spend concentrates before committing to
  a Sarvam plan tier: log `model_used` from every `route_completion` /
  `route_translation` result (already returned in the result dict, just not
  persisted yet) for a day of real traffic, and count how often each tier
  actually gets used.
