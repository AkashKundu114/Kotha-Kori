# V3 Code Pass — What Changed, What's Still Open

Scope: Features 1 (Voice-Ledger), 3 (Catalog Creator), 8 (Market Predictor)
only. Feature 2 (Scheme RAG) intentionally unwired, not deleted.

## What this pass fixed/built

**Feature 1 (Ledger) — completed, not just refined.**
The prior pass had `ledger_extract_node.py` producing a confirmation message
with nothing downstream to act on it. This pass adds:
- `ledger_confirm_node.py` — actually writes to `ledger_entries` on "হ্যাঁ",
  applies corrections on "না"/digit-containing replies, loop-guards after 3
  failed rounds instead of confirming forever.
- `graph.py`'s new entry routing (`route_active_flow` logic in
  `_route_after_profile_load`) — the actual bug fix. A reply while
  `awaiting_confirmation=True` now skips intent classification entirely.
- `ledger_report_node.py` + `pdf_service/generator.py` — "রিপোর্ট" now
  actually generates and sends a PDF; previously `pdf_service` existed with
  no caller anywhere in the graph.
- Personalized confidence floor in `ledger_node.py`, per the user model.

**Feature 3 (Catalog Creator) — built from nothing.**
Did not exist before this pass. New: `rembg_processor.py` (background
removal), `vision_router.py` (product ID + captioning, local-first cascade
via a new `route_vision_completion` in `model_router.py`), `catalog_node.py`
(ties it together, S3 round-trip, audit row), plus gateway changes to
actually download and stage the incoming image (v2's gateway only ever
handled audio/text).

**Feature 8 (Market Predictor) — built from nothing.**
New: `aggregator.py` (k-anonymized block-level ledger aggregation — read the
docstring, the k=5 floor is load-bearing for privacy, don't lower it casually),
`agmarknet_client.py` (external price signal, best-effort/non-blocking),
`market_predictor_node.py` (deterministic trend classification + LLM only for
phrasing, never for the classification itself).

**Cut across all three:** idempotency + rate limiting in `gateway/main.py`
(P0 items from `../security/SECURITY_AUDIT_V3.md`), since I was already refining that
file to add image handling — no reason to leave known P0 gaps in code I was
touching anyway.

## What I did NOT verify and you must before relying on it

1. **Agmarknet API shape** (`agmarknet_client.py`) — flagged explicitly in
   its docstring. The exact resource ID/response schema needs checking
   against the live API; I wrote the caller contract to degrade gracefully
   (returns `[]` on any failure) specifically because I couldn't verify this.
2. **rembg/onnxruntime install on your actual GPU box** — CPU build
   specified deliberately (see `requirements-v3-additions.txt`), but confirm
   it doesn't fight the Ollama/Whisper GPU processes for CPU threads under
   real concurrent load during the pilot.
3. **Onboarding flow that creates the initial `users` row with the new V3
   columns** — `user_profile_node.py` reads them; nothing in this pass
   writes them for a brand-new user. That's the Week-2 onboarding Flow work
   from `../planning/SPRINT_V3_PLAN.md`, still open.
4. **`ledger_correction_rate` is read but never recomputed** — the schema
   and read-side personalization logic are in place; the write-side job
   (recompute per user, e.g. nightly, from `ledger_entries.is_corrected`) is
   not written yet. Small, worth doing before you lean on the personalized
   confidence floor for anything real.
5. Run `alembic upgrade head` then `migrations/0003_v3_features.sql`, and
   confirm your Postgres image actually has TimescaleDB before assuming
   `market_prices` is a hypertable — the migration checks for the extension
   and falls back to a plain indexed table if it's absent, but verify which
   path you're actually on.
