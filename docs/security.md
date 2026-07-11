# Security & reliability posture

What's actually enforced in this codebase, and why, so it's reviewable in
one place rather than scattered across commit messages.

## Crash-proofing (the bot never goes silent)

- **Every OpenAI call** goes through `model_router.py`, which sets a hard
  20–25s timeout and the OpenAI SDK's own retry-with-backoff (2 attempts).
  On final failure it raises `ModelUnavailableError` — never an unhandled
  exception.
- **Every orchestrator node** that calls the model catches
  `ModelUnavailableError` and replies with a friendly Bengali "try again in
  a bit" message instead of leaving the user in silence.
- **`celery_entrypoint.py`** wraps the entire graph invocation in try/except
  — a bug in any node degrades to an error message, not a dead task.
- **`gateway/main.py`**'s webhook handler never raises past a 200 response —
  Meta gets acknowledged regardless of what happens downstream, so a bad
  payload can't trigger a retry storm.
- **STT cascade** (`provider_cascade.py`) tries OpenAI Whisper, then falls
  back to a free self-hosted `faster-whisper` model — a single provider
  outage doesn't take voice input down.

## Abuse / cost-exhaustion protection

- **Idempotency**: every webhook message ID is deduplicated in Redis (24h
  TTL) before it's ever queued — Meta's own webhook retries can't create
  duplicate financial records.
- **Per-number rate limiting**: 30 messages/hour by default
  (`MAX_MESSAGES_PER_HOUR`), enforced before a message is queued for LLM
  processing.
- **Input size caps**: audio capped at 6MB, images at 5MB, checked against
  Meta's reported `file_size` before download completes where possible (not
  just after). Text messages are truncated to `MAX_TEXT_MESSAGE_CHARS`.
- **Amount validation**: `_validate_amount` in `ledger_confirm_node.py`
  rejects NaN/Infinity and anything above ₹5,00,000 per transaction before
  it reaches the database — a bad extraction can't silently corrupt a
  profit/loss report.
- Set a spend cap on the OpenAI dashboard as a second, platform-level
  control independent of the app-level rate limit.

## Data protection

- Webhook signatures are verified with `WA_APP_SECRET` (HMAC-SHA256) — kept
  distinct from `WA_WEBHOOK_VERIFY_TOKEN`, which is only used in the
  one-time GET handshake and is not a secret in the same sense.
- Postgres and Redis are bound to `127.0.0.1` only in `docker-compose.yml`
  — never exposed to the host's public network interface — with Redis
  additionally requiring a password.
- All containers run as a non-root `appuser`.
- The PDF renderer (`pdf_service/generator.py`) has `autoescape=True`, a
  tag-stripping `_clean()` pass on every field that can originate from user
  voice input, and `base_url=None` so WeasyPrint has no legitimate reason to
  fetch remote resources — closing the SSRF/injection path a naive
  HTML-to-PDF pipeline would otherwise have.
- Market trend data enforces a k-anonymity floor of 5 distinct sellers
  (`MIN_SAMPLE_SIZE` in `aggregator.py`) at the query level, not as a
  post-hoc filter — no trend is ever computed from fewer than 5 people's
  income data.

## Sarvam AI integration

- Same treatment as OpenAI: every Sarvam call has a timeout, and any failure
  raises `SarvamUnavailableError`, caught inside `model_router.py` and
  translated into a fall-through to the next tier — a Sarvam outage degrades
  service quality (falls back to OpenAI), it never crashes a turn.
- The Banglish-normalization translation call is gated by a cheap, offline
  character-ratio heuristic (`_looks_code_mixed`) before it ever touches the
  network — this is a cost control, not just a performance one: without it,
  every single voice note would trigger an extra billed API call regardless
  of whether translation was actually needed.
- `SARVAM_API_KEY` is entirely optional — its absence is not an error state,
  just a routing decision (everything falls to OpenAI). No code path treats
  a missing Sarvam key as a failure.
- Ad-poster generation reads a local font file path (`BENGALI_FONT_PATH`)
  and never writes to it — a missing or invalid path degrades to skipping
  the poster composite, logged as a warning, never a crash. Poster output is
  a JPEG re-encode (Pillow), not something WeasyPrint-style with any network
  fetch capability, so it doesn't reopen the SSRF class of issue the PDF
  generator specifically closes.

## Known, deliberate limitations (not oversights)

- No mTLS between internal services — acceptable at single-VM pilot scale
  where Docker's network is the trust boundary; revisit before a multi-node
  deployment.
- No IP-allowlisting of Meta's webhook ranges at the app level — do this at
  your cloud firewall/security-group layer instead (search "WhatsApp Cloud
  API webhook IP ranges" for the current list before a real launch).
- The local-model fallback (`USE_LOCAL_MODELS=true`) is optional and off by
  default — it needs a GPU box you provision yourself; nothing about
  production-readiness depends on it.
