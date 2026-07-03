# Kotha-Khata V3 — Security Audit & Production Readiness
**Method:** Read the codebase as an attacker looking to (a) corrupt financial data, (b) burn API budget, (c) exfiltrate PII, (d) take the service down. Findings below are real, specific to files in the repo, not generic checklist items.

---

## P0 — Fix before any public user touches this

### H1. No webhook replay / idempotency protection → duplicate financial records
**File:** `services/gateway/main.py`
**Exploit:** Meta retries webhooks on timeout by design. An attacker (or just network flakiness) causes the same `message.id` to hit `_dispatch_to_orchestrator` twice → two ledger entries for one sale → wrong P&L → wrong bank-submission PDF. This is the single worst thing that can happen to this product's core trust proposition.
**Note:** the old v1 TRD (§4.1) explicitly specified this ("Idempotency: check `message.id` against Redis dedup set (TTL 24h)") — it just never made it into v2's actual `main.py`.
**Fix:**
```python
# in receive_message(), before background_tasks.add_task(...)
s = get_settings()
redis = await get_redis()
was_new = await redis.set(f"dedup:{msg.message_id}", "1", ex=86400, nx=True)
if not was_new:
    return {"status": "ok"}  # already processed, silently ack
```

### H2. No rate limiting enforced → cost-exhaustion DoS
**File:** `shared/config/settings.py` has `max_messages_per_hour: int = 30` but **nothing in the codebase reads this field**. `services/gateway/middleware/__init__.py` is empty.
**Exploit:** A single scripted number sends thousands of scheme-RAG queries → every one is `SAFETY_CRITICAL` → always Claude → your Anthropic bill spikes with zero product benefit. This is the most likely way a "successful pilot" quietly becomes an expensive incident.
**Fix:** sliding-window counter in Redis, checked in `receive_message` before queueing:
```python
key = f"ratelimit:{msg.from_number}:{int(time.time()//3600)}"
count = await redis.incr(key)
await redis.expire(key, 3600)
if count > s.max_messages_per_hour:
    await send_text(msg.from_number, "আপনি অনেকবার মেসেজ পাঠিয়েছেন। একটু পরে চেষ্টা করুন।")
    return {"status": "ok"}
```

### H6. Audio "delete within 60s" is a written promise, not code
**Files:** `docs/archive/product/trd.md` §7.1 and `docs/product.md` §6 both state audio is deleted within 60 seconds of transcription. No file in the v2 codebase does this — audio bytes are downloaded and passed in-memory but there's no explicit S3 lifecycle rule or deletion call anywhere.
**Why P0:** This isn't just a bug — it's a compliance claim you'd be making to real rural women during consent onboarding that isn't technically true. Fix before enrolling a single real user.
**Fix:** Either (a) never persist raw audio to S3 at all for the pilot (simplest — process in-memory, discard after STT, which is what the code already effectively does — just document it accurately), or (b) if you do persist for STT-eval/fine-tuning purposes, add an S3 lifecycle rule (`Expiration: 1 day`) and update the consent copy to say what actually happens.

### H9. No size/duration caps on uploaded media → resource exhaustion
**File:** `shared/whatsapp/media.py` — `download_whatsapp_audio` has no size check before download or before handing to `ffmpeg`/Whisper.
**Exploit:** A malicious or buggy client sends an oversized/malformed audio blob; ffmpeg or the GPU worker chokes on it, degrading the shared voice-gateway for every other pilot user (single-GPU box = shared blast radius at this scale).
**Fix:** Validate `Content-Length`/media metadata against a cap (PRD already specifies: 3 min voice, 5MB image) before download completes; reject with a friendly Bengali message otherwise.

### H12. No abuse/spam guard on onboarding or scheme queries
**Exploit:** Nothing stops a script from onboarding thousands of fake numbers or hammering the eligibility flow — each one costs an LLM call. At pilot scale this is a budget risk more than a security one, but it compounds with H2.
**Fix:** Cheapest effective control for a 2-week pilot — restrict `/webhook/whatsapp` at the infra layer (security group / WAF rule) to Meta's published webhook IP ranges (TRD §7.2 already names this control, just wasn't implemented in v2's `main.py`). Combine with H2.

---

## P1 — Fix in week 2, before scaling past the pilot cohort

### H3. Vector literal built via f-string interpolation in raw SQL
**File:** `services/rag_service/pipeline.py` — `emb_str` is spliced directly into the `SELECT` text rather than bound as a parameter (the `scheme_clause`/`:schemes` param *is* done correctly right next to it, which makes the inconsistency easy to miss in review).
**Practical risk today:** low — `emb_str` is built from floats returned by your own Ollama embedding call, not user input. **Risk tomorrow:** if this pattern gets copy-pasted into a node that embeds anything closer to raw user input, it's a live SQL injection. Fix now while it's cheap:
```python
# pass as a bound parameter instead of an f-string
params["embedding"] = emb_str
# ... "1 - (sc.embedding <=> :embedding::vector) AS similarity" ...
```

### H5. No service-to-service auth between internal services
`voice-gateway`, `pdf-service`, `ollama` all sit on the docker-compose network with no auth between them. Fine for a single-VM pilot (network isolation via the compose network *is* your boundary at this scale). **Do not** carry this into a shared Kubernetes namespace without adding the mTLS/JWT the original TRD §7.2 specified — flag this explicitly in the doc so it doesn't get forgotten during the Phase-2 infra jump.

### H7. Secrets management — pilot-appropriate, not enterprise-appropriate
`.env` + k8s `secretRef` is fine for a single-VM pilot. Just don't commit a real `.env` (check `.gitignore` covers it — `.gitattributes` in the repo doesn't confirm this, verify manually) and rotate the WhatsApp/Anthropic/Sarvam keys once after the pilot before any wider launch, since they'll have sat in a dev `.env` file.

### H10. No alerting on the failure modes that matter most
You don't need PagerDuty for 20 users. You do need **one** alert: Langfuse or a simple cron script that checks `rag_hallucination_events` / grounding-verifier `all_grounded=False` rate hourly and pings you on Telegram/WhatsApp/Slack if it spikes — a wrong scheme answer is the one failure mode with real consequences for a real person, so it's the one thing worth watching manually every single day of the pilot regardless of tooling maturity.

---

## P2 — Note and defer (correct call for a 2-week pilot, wrong call forever)

- **H4** CORS `*` in `services/gateway/main.py` — harmless while the only client is Meta's webhook; tighten before any dashboard/browser client is added.
- **H8** `asyncio.run()` per Celery task — works fine at pilot concurrency; revisit with `asgiref`/a persistent event loop only if you see worker latency creep under load.
- **H11** Unvalidated WhatsApp Flow `interactive_payload` — add a pydantic schema once Flow-driven eligibility (Internship Guide Option C) actually ships.

---

## Production-readiness checklist (MLOps/DevOps lens, sized to pilot scale)

- [ ] Single GPU VM (RTX 4090-class) runs `docker-compose.yml` as-is — no Kubernetes for this phase
- [ ] Nightly `pg_dump` → S3, tested restore once before go-live
- [ ] Langfuse dashboard checked daily during pilot (manual, by you — that's the actual "monitoring" at this scale)
- [ ] `make test` green in CI on every push (GitHub Actions — even a minimal lint+test workflow beats none)
- [ ] Staging smoke test: one real voice ledger entry, one real scheme question, one real product photo — done end-to-end on the actual WABA test number before flipping to production number
- [ ] Consent copy in onboarding accurately reflects what H6's fix actually does with audio (don't ship a compliance claim you haven't verified in code)
- [ ] All P0 items above closed
- [ ] Rollback plan: if grounding-verifier failure rate spikes, you can flip `SCHEME_RAG` routing to return the safe fallback message for *all* queries with a one-line env flag — worth adding as a kill switch given how consequential a wrong scheme answer is
