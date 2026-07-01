# User Model & Research Plan
Covers two of your mentor's asks: (1) a per-user model that personalizes responses, and (2) what to build/measure so this becomes a defensible research paper + conference submission, not just a working bot.

---

## Part 1 — Per-User Model

### Design decision (with the alternatives I rejected)
- *Option A: pack everything into `users.metadata JSONB`* (as the old schema already stubs) — rejected as the sole store. Fine for low-write fields, bad for fields that update every turn (e.g. correction rate) — JSONB read-modify-write under concurrent Celery workers risks lost updates.
- *Option B: a separate `user_profiles` table, one row per user, updated via targeted column writes* — **chosen**. Keeps hot fields (correction_count, last_confidence) cheaply updatable, keeps PII (name, phone) in `users` untouched (already correctly separated per TRD §7.1), and keeps the profile queryable for research analysis later without touching the PII table at all — good for your DPDP posture and for anonymized research export.

### Schema
```sql
CREATE TABLE user_profiles (
  user_id UUID PRIMARY KEY REFERENCES users(id),

  -- Collected once, at onboarding (via WhatsApp Flow — no LLM round-trip, see ARCHITECTURE.md #3)
  business_categories TEXT[],          -- ['papad', 'kantha', 'poultry', ...]
  self_reported_literacy TEXT,          -- 'reads_digits_only' | 'functional' | 'comfortable'
  preferred_modality TEXT DEFAULT 'voice', -- 'voice' | 'text' | 'both'
  dialect_hint TEXT,                    -- 'rarhi' | 'barendri' | 'standard' | ... (self-selected or inferred)
  network_tier TEXT,                    -- '2g' | '3g' | '4g' (inferred from media round-trip latency, not asked)

  -- Updated continuously from behavior (this is what makes it a *model*, not a form)
  ledger_correction_rate FLOAT DEFAULT 0.0,   -- corrections / total confirmations, rolling 30d
  avg_stt_confidence FLOAT,
  scheme_queries_count INT DEFAULT 0,
  sessions_count INT DEFAULT 0,
  last_active_at TIMESTAMPTZ,
  trust_stage TEXT DEFAULT 'new',       -- 'new' | 'building' | 'established' — see routing use below

  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### How it actually changes behavior (this is the part that matters — a stored profile nobody reads is just a database, not a "model")

1. **Confidence floor personalization in `model_router.route_completion`** — a user with a high historical `ledger_correction_rate` gets a *higher* `confidence_floor` passed in (escalate to Claude more readily for them specifically), because the local model has empirically been wrong for this person more often. This is a genuinely novel routing signal — most cascade systems route by task type only, not by *per-user* historical reliability.
2. **Response modality** — `preferred_modality` (or `self_reported_literacy = 'reads_digits_only'`) triggers auto-attaching a TTS audio version of every text confirmation (Bhashini/Sarvam TTS, already in your stack per `sarvam_provider.py:synthesize`), instead of making the user ask for voice output.
3. **Confirmation verbosity** — `trust_stage == 'new'` gets the full itemized confirmation message (build trust by showing exactly what was understood); `trust_stage == 'established'` (say, 30+ successful sessions with low correction rate) gets a shorter confirmation, reducing message count/data cost for a user who's proven the extraction works for them.
4. **Scheme RAG framing** — `business_categories` filters which schemes get proactively surfaced in the help menu / disambiguation prompts (a poultry-only user doesn't need Sabooj Sathi bicycle-scheme prompts).

### Where it's read from
Add a `user_profile: dict | None` field to `ConversationState` (`services/orchestrator/state.py`), populated by a lightweight `load_user_profile` node that runs immediately after `classify_intent`, before any feature node. Every downstream node (`ledger_extract_node`, `scheme_rag_node`) reads `state["user_profile"]` for the personalization hooks above — same pure-function pattern as the rest of the graph, nothing new to learn.

### Collection flow
Add an onboarding WhatsApp Flow screen (same mechanism as `scheme_eligibility_flow.json`) asking: business type (multi-select), literacy comfort (3 options, phrased respectfully — see PRD's careful tone), preferred voice/text. Structured, no LLM cost, matches the existing "Flows for structured intake" architecture decision.

---

## Part 2 — What "normal AI tools" genuinely cannot do here (your paper's actual contribution)

Don't oversell generic RAG/voice-bot claims — reviewers will have seen a hundred of those. Here's what's real and specific to this build:

1. **Per-claim, per-scheme grounding verification for orally-consumed answers.** Your `grounding_verifier.py` already catches "right number, wrong scheme" hallucinations — a failure mode generic RAG demos rarely test for, and one with real financial consequence when the answer is read aloud to someone who can't cross-check it against the source document herself. This is your strongest, already-built technical contribution — lead with it.
2. **User-model-conditioned cascade routing** (Part 1, point 1 above) — routing that adapts per-user reliability history, not just per-task-type. Worth a small ablation in the paper: fixed confidence floor vs. per-user adaptive floor, measured against correction rate.
3. **Voice-first, zero-app-install, zero-literacy-required deployment on infrastructure the target group already has** (WhatsApp) — the contribution here is the *field validation*, not the tech; a generic AI tool assumes literacy and app adoption that this population doesn't have.
4. **Outcome-grounded evaluation, not just NLP-metric evaluation** — measure whether a generated PDF was actually accepted by a bank, whether a scheme checklist actually resulted in a submitted application. This is rare in NLP papers and is your differentiator for a "social good" venue over a pure-ML venue.

---

## Part 3 — Research paper & field-work plan

### Working title
*"Voice-First, Citation-Grounded Financial and Welfare Assistance for Low-Literacy Rural Women: A WhatsApp Field Deployment in West Bengal"*

### What to measure (instrument this from day 1, not retroactively)
| Metric | How | Source |
|---|---|---|
| STT WER by dialect | Weekly, `scripts/eval_stt.py` against a labeled 50-100 sample set per dialect | `data/training-audio/eval-set/` |
| Ledger extraction accuracy | Correction rate proxy (already in user model) + manual audit of 100 samples | `ledger_entries.is_corrected` |
| RAG hallucination rate | `grounding_verifier` output logged for every query, weekly human audit of a sample (`scripts/audit_rag.py`) | Langfuse traces |
| **Real-world outcome**: PDF bank-acceptance rate | Follow-up WhatsApp survey at day 14/30: "did you show this PDF to a bank/NGO? was it accepted?" | New survey flow, low effort to add |
| **Real-world outcome**: scheme checklist → application submitted | Same follow-up survey pattern, per `scheme_interactions.user_confirmed_applied` (schema already has this field, just needs a reminder flow to populate it) |
| Onboarding completion, retention | Standard funnel metrics, already tracked implicitly via `users.onboarded_at` / `last_active_at` |

### Field work protocol
1. Partner with 1 NGO (start with whichever district your mentor/network already has a contact in — don't cold-approach for a 2-week timeline).
2. Recruit 15-30 pilot users through the NGO's existing SHG WhatsApp groups (matches the PRD's own onboarding assumption — no new behavior required from users).
3. Consent: explicit, in Bengali, voice or text, before any data collection — capture consent_given + consent_given_at as the schema already requires. For video interviews specifically, get a **separate** written/recorded consent naming exactly how the video will be used (research paper, conference talk) — don't bundle it into general product consent.
4. Structured interview guide (bring this to field visits, ~15 min per participant):
   - What did you use it for, unprompted (don't lead with feature names)
   - Walk me through the last time you used it — what worked, what confused you
   - Did you show anyone (bank, panchayat, family) anything it produced? What happened?
   - What would you want it to do that it doesn't?
5. Video interviews: 3-5 in-depth, consented, in the user's own words — this is what makes a conference talk land emotionally, not just technically. Budget a full field day for this, don't rush it into the same visit as bulk onboarding.

### Venue targets (verify current CFPs — my knowledge may be stale by the time you submit)
Reasonable fits based on the shape of this work: ACM COMPASS (Computing and Sustainable Societies), workshops on ML/NLP for social good at ACL/EMNLP/NeurIPS, and India-specific venues (e.g., ACM IKDD CODS, or AI4Bharat-adjacent workshops) given the Indic-language and government-scheme-access angle. **Search for current calls before committing** — conference cycles and workshop topics shift yearly and this is exactly the kind of fact that goes stale.

### Realistic timeline
- Weeks 1-2 (this sprint): build + launch + instrument metrics
- Weeks 3-6: pilot runs, weekly hallucination audits, field visits, video interviews
- Weeks 7-8: write-up, using the metrics table above as your results section skeleton
- Don't submit before you have at least the STT WER, extraction accuracy, and hallucination rate numbers from real pilot traffic — a paper with only architecture and no field numbers will read as a systems demo, not a research contribution, and reviewers at these venues specifically look for field validation.
