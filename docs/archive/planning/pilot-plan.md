# Two-Week Plan: Finish, Deploy, and Pilot Features 1, 3, 8

Scope: **Feature 1 (Voice-Ledger), Feature 3 (Catalog Creator), Feature 8 (Market Predictor)**.
Feature 2 (Scheme RAG) is code-complete but intentionally out of this pilot's routing —
don't re-enable it mid-sprint; that's a separate, deliberate scope decision already
made in `docs/archive/planning/scope.md`.

This plan assumes the code state described in `docs/archive/engineering/code-pass-notes.md`:
all three features are wired into `graph.py`, but security/hardening items and the
onboarding→user-model write path are still open. **This is a finish-and-ship plan, not
a build-from-zero plan** — most of the hard engineering is already done; the risk here
is entirely in ops, security, and field logistics.

---

## Week 0 — before Day 1 (do this today, not on the sprint clock)

These are the items from `docs/archive/operations/manual-tasks.md` with unpredictable
external timelines. Start them now so they don't block Week 2's pilot launch.

- [ ] Meta Business verification submitted (1–4 week external review — the single
      biggest schedule risk in this whole plan)
- [ ] Bhashini/ULCA registration submitted (government registration, days not minutes)
- [ ] NGO partner conversation started (relationship, not an account — no code fixes this)
- [ ] Anthropic API key + billing + spend cap set
- [ ] GPU box (RTX 4090-class) provisioned for Ollama + Whisper fallback

If Meta business verification isn't done by the time you need real (non-test) numbers,
run the entire pilot on the 5 allow-listed test numbers — that's enough for a
10–20 person pilot and doesn't block anything in Weeks 1–2 below.

---

## Week 1 — Close known gaps, apply P0 security fixes, no new scope

| Day | Work | Definition of done |
|---|---|---|
| 1 | **Idempotency + rate limiting** (`security.md` H1/H2) — verify these are actually live in `gateway/main.py`, not just documented | `redis dedup:` keys visible under load test; 31st message/hour in a test loop gets the soft-block reply, not processed |
| 1 | **Webhook HMAC fix** (`red-team.md` HIGH-1) — confirm signature check uses `wa_app_secret`, separate from `wa_webhook_verify_token` | Send a request signed with the wrong secret; confirm 403 |
| 2 | **Network exposure fix** (`red-team.md` CRIT-1) — bind Redis/Postgres/Ollama to `127.0.0.1` only in `docker-compose.yml`; add `requirepass` to Redis | `redis-cli -h <public-ip>` from outside the box refuses connection |
| 2 | **PDF SSRF fix** (`red-team.md` CRIT-2) — `autoescape=True`, strip tags on all user-derived template fields, `HTML(..., base_url=None)` | Feed a category string containing an `<img src=...>` tag through the ledger correction flow; confirm it renders as literal text in the PDF, not a tag |
| 3 | **Ledger amount bounds + exception handling** (`red-team.md` HIGH-4) — `_validate_amount`, wrap `graph.ainvoke` in try/except in `celery_entrypoint.py` | Voice note with an absurd/negative amount gets a friendly Bengali retry message, not silence |
| 4 | **Audio size cap** (`red-team.md` HIGH-2) — confirm `MAX_AUDIO_BYTES` cap is enforced pre-download, not just post-download | Oversized audio blob rejected with friendly message before hitting the GPU |
| 4 | **Grounding-verifier word-form fix** — not on the pilot's critical path (Scheme RAG isn't routed in V3), but cheap to land now since it's already specified in `red-team.md` HIGH-3 | New test passes: `test_word_form_hallucination_is_caught` |
| 5 | **Docker non-root users** (`red-team.md` MED-1) across all 5 Dockerfiles | `docker exec <container> whoami` returns `appuser`, not `root` |
| 5 | **`.env` hygiene check** — confirm `.gitignore` actually excludes `.env`, check `git log` for accidental commits, rotate any key that was ever committed | `git log --all --full-history -- .env` returns nothing |

**End of Week 1 exit criteria:** every P0/CRIT/HIGH item in both security docs is closed
or explicitly deferred with a one-line reason in the docs (don't silently drop one —
see `security.md`'s own P2 section for the right pattern: "note and defer" is
a legitimate outcome if you write down why).

---

## Week 2 — User model, load test, staging smoke test, go-live

| Day | Work | Definition of done |
|---|---|---|
| 6 | **Onboarding writes the V3 user columns** (`V3_CODE_PASS_NOTES.md` open item #3) — `onboarding_node.py` currently only sets `name`/`block`/`consent_given`; add `business_categories`, `self_reported_literacy`, `preferred_modality` via a WhatsApp Flow screen, same pattern as `scheme_eligibility_flow.json` | New user's row in `users` has all V3 columns populated, not null |
| 7 | **`ledger_correction_rate` recompute job** (`V3_CODE_PASS_NOTES.md` open item #4) — nightly job, `is_corrected` count / total confirmations, rolling 30d | Cron/Celery-beat job runs once against test data; user's stored rate updates |
| 8 | **Load test** — Locust, 10x expected pilot volume (20 users × generous margin ≈ 200 concurrent webhook POSTs is already generous; TRD's original 10,000 target is Phase-3 scale, don't chase it here) | No 5xx errors, P95 webhook ack < 500ms under test load |
| 9 | **Staging smoke test on real WABA test number** — one real voice ledger entry end-to-end, one real product photo through Catalog Creator, one market report request | All three produce correct WhatsApp replies within latency budget (TRD §8.3) on a real phone, not curl |
| 9 | **Nightly `pg_dump` → S3 backup**, tested restore once | Restore succeeds against a scratch DB before go-live, not after |
| 10 | **Consent copy final review** — Bengali, DPDP-Act-aware, reviewed by someone with actual legal familiarity if at all possible (see `MANUAL_TASKS_GUIDE.md` #12) | Signed off, not just drafted |
| 11 | **NGO onboarding call** — get 10–20 real pilot users consented (this is the field-work handoff — see `fieldwork.md`) | Enrollment list with consent timestamps |
| 12–14 | **Live pilot monitoring** — check Langfuse daily for grounding/error-rate spikes, fix whatever breaks first (it won't be what you predicted) | Daily check logged; any P0-severity bug gets a same-day patch |

---

## Explicit non-goals for this two weeks (say no to these if asked)

- Kubernetes, Istio, multi-region DR — Phase-3 scale infra, not pilot infra (`scope.md` §4 already made this call)
- Re-enabling Scheme RAG in routing — separate scope decision, don't reverse it mid-sprint
- Fine-tuning Whisper/Qwen on pilot data — that's the *output* of this pilot, not an input to it (see `LLM_GUIDE.md`'s phased migration plan: fine-tuning happens post-pilot, using data this pilot generates)
- SMS/USSD fallback, multi-language expansion — Phase 3 roadmap items

## Rollback plan (write this down before go-live, not during an incident)

- Grounding-verifier failure rate spike → not applicable this pilot (Scheme RAG not routed), but keep the kill-switch pattern in mind for when it's re-enabled
- Ledger data-loss report from any user → freeze ledger writes immediately, manual audit before resuming (per `IMPLEMENTATION_PLAN.md` §5.4)
- STT accuracy visibly degrading → cascade already auto-falls-through Sarvam → Bhashini → local Whisper; if all three degrade, that's a GPU-box or network incident, not a model problem — check `voice-gateway` container health first
- WABA suspended → pre-drafted Bengali explanation template ready to send via Gupshup backup number (confirm this backup path is actually configured, not just planned, before Day 11)
