# Voice-First, Citation-Grounded Financial and Welfare Assistance for Low-Literacy Rural Women: A WhatsApp Field Deployment in West Bengal

**Status: Draft skeleton.** Sections 1–4 and 6–7 are ready to refine now. Section 5
(Results) has the table structure and framing in place but is intentionally left as
placeholders — filling it with invented numbers would misrepresent the work. Run the
pilot per `SPRINT_2WEEK_PLAN.md` and the fieldwork in `FIELD_RESEARCH_TOOLKIT.md`
first, then populate §5 with real data before submitting anywhere.

---

## Abstract
*(Write this last — 150–200 words summarizing problem, approach, and the single
strongest field-validated result once you have it. Do not write the abstract before
§5 is real; an abstract that promises results the paper doesn't yet contain is the
fastest way to lose a reviewer's trust.)*

---

## 1. Introduction

### 1.1 Motivation
Self-Help Group (SHG) women across rural West Bengal run genuine micro-businesses —
pickle and papad production, Kantha embroidery, poultry, vegetable cultivation — but
face three structural gaps that no amount of entrepreneurial effort closes on its
own: (1) no formal bookkeeping, which makes them ineligible for bank-linkage loans
regardless of actual business health; (2) low awareness of applicable government
welfare schemes, with an estimated 40–60% of eligible women never applying due to
word-of-mouth-only scheme discovery; (3) no market access beyond their immediate
neighborhood. General-purpose AI assistants do not close these gaps — they assume
literacy, a language register (formal Bengali, Hindi, or English) this population
often doesn't use, and sustained engagement with a text interface. WhatsApp, in
contrast, already has near-universal adoption in this demographic; no new user
behavior is required to reach them there.

### 1.2 Contribution
We do not claim algorithmic novelty in any single component — hybrid retrieval,
cascade model routing, and k-anonymized aggregation are all documented 2026
practice. Our contribution is threefold, and is a **systems and field-deployment**
contribution, not a new-ML-method contribution:

1. A **per-claim, per-scheme grounding verifier** for orally-consumed RAG answers
   that catches a specific, underexamined failure mode — "right number, wrong
   scheme" hallucination — which generic RAG evaluation rarely tests for, and which
   carries real financial consequence when the answer is read aloud to someone who
   cannot independently cross-check it against a source document.
2. **User-model-conditioned cascade routing**: a confidence floor for escalating
   from a self-hosted model to a frontier model that adapts to a specific user's
   historical extraction-correction rate, rather than routing purely by task type.
3. **Outcome-grounded field evaluation** — measuring whether generated artifacts
   (ledger PDFs, scheme checklists) were actually accepted by the institutions they
   were meant for, not only whether NLP metrics looked good in a lab setting.

---

## 2. Related Work
*(Fill with actual citations before submission — the categories below are the right
shape, but every claim needs a real, checked source, not a remembered one.)*

- Indic-language voice AI for underserved populations (Bhashini, AI4Bharat, prior
  WhatsApp-based welfare bots in India)
- RAG hallucination detection and mitigation, specifically citation-grounding and
  claim-verification approaches
- Cascade / mixture-of-experts routing for cost-constrained LLM deployment
- Prior HCI/ICTD (Information and Communication Technologies and Development)
  literature on low-literacy interface design and voice-first systems for financial
  inclusion

---

## 3. System Design

### 3.1 Architecture overview
*(Reuse and condense `docs/engineering/ARCHITECTURE.md` here — a LangGraph
state machine, three-tier voice cascade, WhatsApp Flows for structured intake,
criticality-based LLM routing, hybrid RAG retrieval. Include the architecture
diagram from `docs/product/TRD.md` §1, redrawn cleanly.)*

### 3.2 The grounding verifier (primary technical contribution)
Describe the two-pass design: assertion extraction (numeric amounts — both digit
and word forms — and dates) followed by per-chunk, scheme-attributed grounding
checks via a nearby-scheme-name lookback window. Include the concrete
"right-number-wrong-scheme" reproduction case as a worked example — it's a strong,
legible illustration of the failure mode for reviewers unfamiliar with the domain.
State the known limitation honestly: scheme-name detection is a fixed backward
lookback, not full coreference resolution, and does not yet catch cases where the
scheme name follows the amount in a sentence.

### 3.3 Personalized cascade routing
Describe `_personalized_confidence_floor`: the escalation threshold from local model
to Claude adjusts per-user based on rolling 30-day ledger correction rate. Propose
(if pilot data supports it) a small ablation: fixed floor vs. adaptive floor,
measured against downstream correction rate and Claude-escalation frequency.

### 3.4 Privacy design
Describe the k-anonymity floor (`MIN_SAMPLE_SIZE = 5`) in the market-aggregation
pipeline as a privacy mechanism enforced at query time, not as a post-hoc filter.

---

## 4. Methodology (field study)

### 4.1 Deployment context
State district(s), NGO partner, number of SHG groups involved, and the pilot
duration, once known.

### 4.2 Participants
State actual N once recruited (target: 15–30 per `FIELD_RESEARCH_TOOLKIT.md` §1.1),
broken down by SHG-member / group-leader / independent-entrepreneur, with age range
and business-category distribution.

### 4.3 Data collection
- Quantitative: STT WER by dialect (weekly eval, `scripts/eval_stt.py`), ledger
  extraction accuracy (correction-rate proxy + manual audit), RAG grounding-check
  pass rate.
- Qualitative: structured interviews (`FIELD_RESEARCH_TOOLKIT.md` §3), 3–5
  in-depth video interviews.
- Outcome: day-14/30 WhatsApp follow-up survey on PDF bank-acceptance and scheme
  application submission.

### 4.4 Ethics
State the two-tier consent process (§2 of `FIELD_RESEARCH_TOOLKIT.md`), DPDP Act
2023 compliance posture, and — if applicable — IRB/ethics-board approval status for
your institution. Do not omit this section even in a systems-track submission;
reviewers in this space specifically check for it given the vulnerable population.

---

## 5. Results — *placeholder, populate after fieldwork*

### 5.1 Quantitative results

| Metric | Target | Result | N |
|---|---|---|---|
| STT WER (rural Bengali dialects) | ≤ 92% | *TBD* | *TBD* |
| Ledger extraction accuracy | ≥ 88% | *TBD* | *TBD* |
| RAG grounding-check pass rate | *TBD baseline* | *TBD* | *TBD* |
| Onboarding completion rate | ≥ 70% | *TBD* | *TBD* |
| Week-2 retention (≥1 ledger entry) | ≥ 50% | *TBD* | *TBD* |

### 5.2 Outcome-grounded results

| Outcome | Result |
|---|---|
| PDF reports generated | *TBD* |
| PDFs reported accepted by a bank/NGO (self-report, day 14/30 survey) | *TBD* |
| Catalog Creator images actually shared with a customer | *TBD* |
| Reported sales resulting from a shared catalog image | *TBD* |

### 5.3 Qualitative findings
Summarize recurring themes across interviews (§3 of the toolkit) once transcribed.
Use direct quotes only from participants who consented to attribution per
`FIELD_RESEARCH_TOOLKIT.md` §2.2, and only short, clearly-marked quotes — don't
paraphrase in a way that implies precision you don't have from field notes alone.

---

## 6. Discussion

### 6.1 What worked
*(Fill in once §5 exists — likely candidates based on the design: voice-first
onboarding reducing literacy barriers; confirm/correct loop building trust over
repeated sessions per the `trust_stage` mechanism.)*

### 6.2 Limitations
- Small pilot N (15–30) — results are directional, not statistically powered for
  strong generalization claims. Say this explicitly; don't let a reviewer find it first.
- Grounding verifier's scheme-attribution is a lookback heuristic, not true NER —
  document this as an open engineering limitation, not just a paper caveat.
- Scheme RAG (Feature 2) — the component most directly tied to the "hallucination
  prevention" contribution claim — was not in this pilot's live routing. If the
  paper's headline claim leans on grounding-verifier performance, either (a) report
  it as an offline/synthetic evaluation result clearly labeled as such, or (b) run
  a small supplementary live evaluation before submission. Don't imply live-pilot
  validation of a feature that wasn't live in the pilot.

### 6.3 Threats to validity
Self-selection in NGO-recruited participants; social-desirability bias in
interview responses (participants may overstate usefulness to a researcher they
were introduced to by a trusted NGO coordinator); short pilot duration relative to
scheme-application timelines (a 2-week pilot likely captures onboarding and early
usage, not full scheme-application-to-approval cycles).

---

## 7. Conclusion
*(Write last, 150 words, tied directly to whatever §5 actually shows.)*

---

## Appendix A — Interview guide
Reuse `FIELD_RESEARCH_TOOLKIT.md` §3 verbatim, with English translations alongside
the Bengali as shown there.

## Appendix B — Consent forms
Reuse `FIELD_RESEARCH_TOOLKIT.md` §2.1 and §2.2 verbatim.

## Appendix C — System prompts
Include the anti-hallucination system prompt from `services/rag_service/pipeline.py`
and the ledger-extraction prompt from `services/orchestrator/nodes/ledger_node.py`,
both already in Bengali with English glosses — useful for reproducibility.

---

## Venue targets (verify current CFPs before committing — conference cycles shift yearly)
ACM COMPASS (Computing and Sustainable Societies) is the closest fit given the
ICTD/social-good framing. ML/NLP-for-social-good workshops at ACL/EMNLP/NeurIPS are
a fit for the grounding-verifier contribution specifically if written as a
standalone technical paper. India-specific venues (ACM IKDD CODS, AI4Bharat-adjacent
workshops) fit given the Indic-language and government-scheme-access angle. Search
for current calls before committing — this is exactly the kind of fact that goes
stale between when this draft is written and when you're ready to submit.
