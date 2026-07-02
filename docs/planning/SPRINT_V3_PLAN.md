# Kotha-Khata — V3 Sprint Plan
## Scope Freeze: Features 1–3 Only → Public Pilot Launch
**Horizon:** 2 weeks to production-usable public pilot | Author's note: written as a decision log, not just a task list — the "why" matters as much as the "what" because you'll be handing pieces of this to other AI coding tools, and they need the constraint, not just the ticket.

---

## 1. The scope decision (and what I rejected)

**Decision:** Ship only Feature 1 (Voice-Ledger), Feature 2 (Scheme RAG), Feature 3 (Catalog Creator). Everything else in the PRD (Agri-Diagnostic, Subsidy Matchmaker, Training, Meeting Minutes, Market Predictor) is explicitly **out of scope** for this sprint.

**Options considered:**
- *Ship all 8 features shallow* — rejected. A rural, low-trust, first-contact user base punishes a bot that half-works far more than one that does 3 things reliably. Trust is the actual product here, not feature count.
- *Ship Ledger + RAG only, defer Catalog* — rejected. Catalog Creator is your most "show, don't tell" demo for a research paper / conference audience (visual before/after), and it's the feature least likely to have a wrong-answer safety consequence — good ROI for engineering effort under time pressure.
- *Ship 1, 2, 3 — chosen.* Matches the Roadmap's own "Ring 1: prove the core loop" philosophy, and all three map cleanly to existing orchestrator nodes or a well-scoped new one.

**Consequence:** Update `docs/product/ROADMAP.md` and `docs/product/PRD.md` headers with a pinned note: *"V3 pilot scope: Features 1–3 only. Features 4–8 remain valid product vision, not current build target."* Don't delete the old docs — a reviewer/conference committee will want to see you had a full roadmap and made a deliberate, defensible cut.

---

## 2. Current state audit (what's actually built vs. what the docs claim)

| Feature | Docs say | Code reality |
|---|---|---|
| 1. Voice-Ledger | Done, MVP-ready | `ledger_node.py`, `ledger_confirm_node.py`, and `ledger_report_node.py` are wired in `graph.py`, including confirmation, DB persistence, and PDF report delivery |
| 2. Scheme RAG | Done, hallucination-guarded | `scheme_rag_node.py` + `grounding_verifier.py` remain available, but V3 routing currently focuses on ledger, catalog, and market flows |
| 3. Catalog Creator | "MVP+" in PRD | Implemented through `services/orchestrator/nodes/catalog_node.py` plus `services/vision_service/` for image analysis and background processing |
| User model / personalization | Not mentioned anywhere in v1 or v2 | **New requirement** — see `docs/research/USER_MODEL_AND_RESEARCH.md` |

This table is your single most important artifact for briefing an AI coding assistant — paste it into the first message of any Claude Code / Cursor session so it doesn't assume more is done than actually is.

---

## 3. Two-week plan

### Week 1 — Close the gaps, don't add scope
| Day | Work | Owner-ready ticket (paste to AI coding tool) |
|---|---|---|
| 1 | Wire ledger DB persistence + confirm/save/discard edges into `graph.py` | "Add `LEDGER_CONFIRM`, `LEDGER_SAVE`, `LEDGER_DISCARD` as LangGraph nodes downstream of `ledger_extract_node`. On user 'হ্যাঁ'/'yes' reply, write `pending_ledger_entry` to `ledger_entries` table via `shared/db/session.py`; on 'না'/no, loop back to extraction with correction context; on 90s timeout, discard. Follow the pure-function node pattern in `ledger_node.py`." |
| 2 | Idempotency + rate limiting (see ../security/SECURITY_AUDIT_V3.md H1/H2) | Paste the H1/H2 remediation spec directly |
| 3–4 | Build Catalog Creator node (Feature 3) | "Build `services/orchestrator/nodes/catalog_node.py`: accept image bytes, call `rembg` for background removal, call a vision model (Ollama `qwen2-vl` or fallback to Claude vision) for product ID + Bengali caption, overlay via Pillow, upload to S3, return `outbound_messages` with image + caption. Register in `graph.py` under a new `catalog` route, triggered by `message_type == 'image'` without agri keywords in caption. Follow the SAFETY_CRITICAL vs ROUTINE split — this is ROUTINE (wrong caption ≠ real-world harm), route through `model_router.route_completion`." |
| 5 | PDF generation node + WhatsApp document delivery, wired to `graph.py` (currently `pdf_service` exists standalone but nothing in the graph calls it) | "Add `ledger_report_node.py`: on 'রিপোর্ট'/'report' trigger, call `pdf_service`'s report generator, get S3 presigned URL, send via `shared/whatsapp/sender.py:send_document`." |

### Week 2 — User model, hardening, and go-live
| Day | Work |
|---|---|
| 6–7 | Implement user model (schema + onboarding Flow + injection into `model_router` prompts) — full spec in `../research/USER_MODEL_AND_RESEARCH.md` |
| 8 | Apply P0 security fixes from `../security/SECURITY_AUDIT_V3.md` (idempotency, rate limit, audio deletion job, input size caps, spam guard) |
| 9 | Load test (Locust, per TRD §10) at 10x expected pilot volume; fix anything that falls over |
| 10 | Deploy to staging with real WABA test number, run the Day-3 trace exercise from `INTERNSHIP_GUIDE.md` end to end with a real voice note in each of the 3 features |
| 11 | NGO partner onboarding call, get 10–20 real pilot users consented and enrolled |
| 12–14 | Live pilot monitoring (watch Langfuse traces daily), fix whatever breaks first in the wild — it will not be what you predicted |

---

## 4. What "production ready" actually means here (don't over-build)

For a 2-week, ~20-user pilot, you do **not** need: Kubernetes, Istio, multi-region DR, or a 4-A100 server. That's Phase-3-scale infrastructure from the old TRD and it will burn your two weeks on infra instead of the product. You need:

- `docker-compose.yml` (already exists) running on a single decent cloud VM (one A10G/RTX4090-class GPU box covers Whisper + Ollama fallback tier at pilot volume)
- Backups: `pg_dump` cron to S3, nightly — that's it for DR at this scale
- Uptime: a single `/health` check + UptimeRobot/Better Stack free tier ping, not full Prometheus/Grafana yet
- Observability: Langfuse (already in compose) is enough; skip Sentry/PagerDuty for now, add if the pilot grows past ~200 users

This is the DevOps/MLOps judgment call: match infrastructure investment to actual current scale, not the Phase-3 vision in the old TRD. Re-evaluate after the pilot, not before.

---

## 5. Handoff note for other AI tools

When delegating a ticket above to Claude Code, Cursor, etc., always paste in this order:
1. The relevant row from the "current state audit" table (§2)
2. The specific ticket text
3. A pointer to the existing pattern file to follow (e.g. `ledger_node.py` as the template for any new node)
4. The constraint: "SAFETY_CRITICAL tasks (money amounts, scheme eligibility) must route through `model_router.route_completion()` with `TaskCriticality.SAFETY_CRITICAL`. Never call Claude or Ollama directly from a node."

This keeps every contributor — human or AI — inside the architecture instead of reinventing it per-file.
