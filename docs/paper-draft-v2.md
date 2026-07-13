# [PLACEHOLDER: Your Full Name]

**[PLACEHOLDER: Your Institution / College Name, or Internship Organization Name]**
**Email: [PLACEHOLDER: your.email@domain.com]**

---

# Catching "Right Scheme, Wrong Number": Citation-Grounded Government Scheme Eligibility in a Voice-First WhatsApp Assistant for Rural West Bengal

### (Working title — see "Title Options" section at the end for two alternates, one per target venue)

**Status: Draft, actively maintained.** Sections 1–4, 6–7, and the Related
Work below are ready to refine now. Section 5 (Results) is intentionally
left as placeholders — filling it with invented numbers would misrepresent
the work. Run the pilot per `docs/archive/planning/pilot-plan.md` and the
fieldwork protocol in `docs/fieldwork.md` first, then populate §5 with real
data before submitting anywhere.

**Changed since the last draft** (see the changelog at the very bottom for
the full list): retitled away from a generic "Intelligent Multilingual
WhatsApp Assistant" framing that overclaimed language coverage and didn't
name the actual contribution; added four real related-work citations found
via literature search (none were in the previous draft); updated the
system description to include the Pricing and Negotiation agents and the
local calendar/product work; updated venue guidance with verified,
currently-live CFP status instead of "verify before submitting" placeholders.

---

## Abstract
*(Write this last — 150–200 words summarizing problem, approach, and the
single strongest field-validated result once you have it. Do not write the
abstract before §5 is real; an abstract that promises results the paper
doesn't yet contain is the fastest way to lose a reviewer's trust.)*

---

## 1. Introduction

### 1.1 Motivation
Self-Help Group (SHG) women across rural West Bengal run genuine
micro-businesses — pickle and papad production, Kantha embroidery,
poultry, vegetable cultivation — but face three structural gaps that no
amount of entrepreneurial effort closes on its own: (1) no formal
bookkeeping, which makes them ineligible for bank-linkage loans regardless
of actual business health; (2) low awareness of applicable government
welfare schemes, with an estimated 40–60% of eligible women never applying
due to word-of-mouth-only scheme discovery; (3) no market access or pricing
confidence beyond their immediate neighborhood, and no bargaining support
when negotiating a sale. General-purpose AI assistants do not close these
gaps — they assume literacy, a language register (formal Bengali, Hindi, or
English) this population often doesn't use, and sustained engagement with a
text interface, a barrier independently documented for exactly this
demographic (Beyond Semantics, FAccT 2025 — see Related Work). WhatsApp, in
contrast, already has near-universal adoption here; no new user behavior is
required to reach them there.

### 1.2 Contribution
We do not claim algorithmic novelty in any single component — hybrid
retrieval, cascade model routing, and k-anonymized aggregation are all
documented practice. Nor do we claim the system is multilingual — it is
deliberately Bengali-first, with an optional English caption variant for
one feature; overstating language coverage would misrepresent the system to
reviewers who will check. Our contribution is a **systems and
field-deployment** contribution, with one genuinely underexamined technical
finding at its core:

1. A **per-claim, per-scheme grounding verifier** for orally-consumed RAG
   answers that catches a specific, underexamined failure mode — "right
   scheme, wrong number" hallucination, where a generated answer attaches a
   real amount from the retrieved context to the wrong government scheme.
   This carries real financial consequence when the answer is read aloud to
   someone who cannot independently cross-check it against a source
   document. This is the paper's lead technical contribution.
2. **User-model-conditioned cascade routing**: a confidence floor for
   escalating from a self-hosted/cheap model to a stronger model that
   adapts to a specific user's historical extraction-correction rate,
   rather than routing purely by task type.
3. **Code-enforced financial guard-rails around LLM-generated language**,
   demonstrated in two agents: a Pricing agent whose recommended price is a
   deterministic function of the seller's own cost/margin/floor (the LLM
   only phrases the explanation), and a Negotiation agent where the LLM is
   structurally prevented from ever generating a price at all — it supplies
   only a digit-free justification fragment, with any generated fragment
   containing a number discarded outright. This generalizes the
   grounding-verifier's "don't trust the model to state the sensitive
   value" principle to a second domain (commerce, not scheme information).
4. **Outcome-grounded field evaluation** — measuring whether generated
   artifacts (ledger PDFs, scheme checklists) were actually accepted by the
   institutions they were meant for, not only whether NLP metrics looked
   good in a lab setting.

---

## 2. Related Work

*(Four citations below were located via literature search and were not in
any previous version of this draft — verify full bibliographic details
against the actual papers before final submission; titles/venues/arXiv IDs
as found, not guaranteed typo-free.)*

**LLM-powered WhatsApp deployments in India, NGO-partnered.**
Closest direct comparator: an LLM-powered, experts-in-the-loop WhatsApp
chatbot built with an NGO in Rajasthan to support the informational needs
of ASHA community health workers (arXiv 2409.10913). Same deployment shape
— India, WhatsApp, LLM, real NGO partnership, HCI4D framing — but addresses
health-worker information needs, not financial recordkeeping or voice-first
extraction, and does not include a hallucination-verification mechanism
comparable to our grounding verifier. Worth an explicit contrast paragraph:
what changes when the domain shifts from "informational lookup" to
"financial figures a bank or the state will act on."

**RAG-powered WhatsApp bots for underserved populations, non-India.**
A RAG-powered WhatsApp chatbot for rural African WASH (water, sanitation,
hygiene) education (arXiv 2411.02850). Same "RAG + WhatsApp + underserved,
low-connectivity population" shape as our Scheme RAG component, validated
via a two-phase expert-then-community review rather than a live grounding
mechanism. Good comparator for framing why our approach adds an automated,
per-claim verification step rather than relying on pre-deployment expert
review alone.

**Voice/ASR barriers specific to this demographic.**
A benchmark and ASR study for rural Bhojpuri-speaking women (arXiv
2506.09653), explicitly motivated by "voice-based access to agricultural
services, financial transactions, government schemes" for exactly this
population, and documenting that current ASR systems perform poorly for
rural women's speech due to data scarcity. Strong citation for motivating
why the STT cascade (Sarvam Saaras V3 → self-hosted fallback) and the
correction-rate-driven confidence floor matter, and a candidate source for
comparing rural-Bengali WER expectations against a comparable
rural-Bhojpuri benchmark.

**Documented literacy/interface barriers for this exact population.**
A qualitative study of LLM chatbot usability with under-represented Indian
women (domestic workers, artisans, varying digital literacy) across three
cities (ACM FAccT 2025), finding that text-heavy chatbot interfaces
requiring precise, grammatically complete queries were a real barrier for
participants with limited formal education. Directly supports the
voice-first design decision as a response to a documented barrier, not an
assumed one.

**Deployed (non-academic) comparator: government scheme eligibility.**
EasyGov (Surajya Services), an Aadhaar-stack civic-tech product offering
AI-powered scheme eligibility checking across 12 Indian languages,
reportedly reaching roughly ten lakh citizens (indiaai.gov.in case study,
not a peer-reviewed source). No stated hallucination-verification
mechanism is described in available public material. Cite as a real-world
comparator to position against, not as academic related work — the
distinction to draw is mechanism-level (a verifiable, per-claim grounding
check) rather than scale or reach, since we cannot and should not claim to
compete on deployment scale.

**Standard categories still needed** (not yet filled with specific
citations — search before submission):
- Hybrid retrieval + reciprocal rank fusion for RAG (general ML literature)
- RAGAS-style faithfulness/groundedness evaluation metrics
- Cascade / mixture-of-cost model routing for cost-constrained deployment
- ICTD/HCI4D literature on low-literacy interface design specifically

---

## 3. System Design

### 3.1 Architecture overview
*(Reuse and condense `docs/architecture.md` here — a LangGraph state
machine, two-tier Sarvam-then-local-Ollama cascade for every agent (no
OpenAI dependency as of the current build — see architecture.md §8),
WhatsApp Flows for structured intake where applicable, criticality-based
routing, hybrid RAG retrieval for the (currently unrouted) Scheme RAG
component.)*

### 3.2 The grounding verifier (primary technical contribution)
Describe the two-pass design: assertion extraction (numeric amounts — both
digit and word forms — and dates) followed by per-chunk, scheme-attributed
grounding checks via a nearby-scheme-name lookback window. Include the
concrete "right-scheme-wrong-number" reproduction case as a worked example.
State the known limitation honestly: scheme-name detection is a fixed
backward lookback, not full coreference resolution, and does not yet catch
cases where the scheme name follows the amount in a sentence.

### 3.3 Personalized cascade routing
Describe the per-user adaptive confidence floor: the escalation threshold
from the cheap model tier to the stronger tier adjusts per-user based on
rolling correction rate. Propose (if pilot data supports it) a small
ablation: fixed floor vs. adaptive floor, measured against downstream
correction rate and escalation frequency.

### 3.4 Code-enforced guard-rails as a generalizable pattern (new section)
This section did not exist in prior drafts and is worth its own
subsection, since it demonstrates the grounding-verifier's core idea
generalizes beyond RAG:

- **Pricing agent**: a recommended price is `f(production_cost,
  preferred_margin, minimum_price, market_average)` — entirely
  deterministic arithmetic. The LLM's only role is to phrase a warm
  explanation of a number it never computes.
- **Negotiation agent**: goes one step further — the LLM is not merely
  *asked* not to state a price, it is structurally prevented from having
  its output used if it does. The model supplies a short justification
  fragment; if that fragment contains a digit *or* a spelled-out number
  word (Bengali number words have no digit glyphs, so a naive digit-only
  filter misses them — this was found and fixed during development, worth
  reporting as a concrete "here is a filter that looked sufficient and
  wasn't" case study), the fragment is discarded outright and a
  deterministic fallback line is used instead. The actual quoted price is
  always interpolated from a value computed in code, never generated.

**Framing for the paper**: this is the same underlying principle as the
grounding verifier (never trust a language model to correctly state a
sensitive, verifiable value — verify or structurally prevent, don't just
prompt-instruct) applied to a second domain. Worth stating explicitly as a
generalizable design pattern for LLM agents that mediate financial
information for a population that cannot independently verify the model's
output, which is the paper's connecting thread across both the RAG and
non-RAG parts of the system.

### 3.5 Privacy design
Describe the k-anonymity floor (minimum distinct-seller threshold) in the
market-aggregation pipeline as a privacy mechanism enforced at query time,
not as a post-hoc filter.

### 3.6 Localization work (brief, supporting section)
Two smaller additions worth a paragraph each, not full sections: (1) a
local West Bengal SHG product taxonomy (papad, Kantha, mustard oil, jute,
terracotta, etc., drawn from the persona interviews / product spec rather
than invented) used to give tighter price-range defaults than a generic
category bucket; (2) a secondary, clearly-labeled Bangla calendar (Bangabda)
date display alongside the authoritative Gregorian date on financial
documents — reported honestly as an *approximation* (fixed Poyla Boishakh
convention, not verified against a specific West Bengal panjika), included
because a "local flavor" is part of what field-work interviews may report
users caring about, not because it changes any legal/financial guarantee
of the system.

---

## 4. Methodology (field study)

### 4.1 Deployment context
State district(s), NGO partner, number of SHG groups involved, and the
pilot duration, once known.

### 4.2 Participants
State actual N once recruited (target: 15–30 per `docs/fieldwork.md` §1.1),
broken down by SHG-member / group-leader / independent-entrepreneur, with
age range and business-category distribution.

### 4.3 Data collection
- Quantitative: STT WER by dialect (weekly eval), ledger extraction
  accuracy (correction-rate proxy + manual audit), RAG grounding-check pass
  rate, and — new — how often the negotiation agent's digit-filter actually
  discards a generated fragment in practice (a direct measure of how often
  the "don't trust the model" design decision earns its keep).
- Qualitative: structured interviews (`docs/fieldwork.md` §3), 3–5
  in-depth video interviews.
- Outcome: day-14/30 WhatsApp follow-up survey on PDF bank-acceptance and
  scheme application submission.

### 4.4 Ethics
State the two-tier consent process, DPDP Act 2023 compliance posture, and
— if applicable — IRB/ethics-board approval status. Reviewers in this space
specifically check for it given the vulnerable population.

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
| Negotiation digit-filter trigger rate | *no target yet* | *TBD* | *TBD* |

### 5.2 Outcome-grounded results

| Outcome | Result |
|---|---|
| PDF reports generated | *TBD* |
| PDFs reported accepted by a bank/NGO | *TBD* |
| Catalog Creator images actually shared with a customer | *TBD* |
| Reported sales resulting from a shared catalog image | *TBD* |
| Negotiated sales completed via the Negotiation agent | *TBD* |

### 5.3 Qualitative findings
Summarize recurring themes across interviews once transcribed. Use direct
quotes only from participants who consented to attribution.

---

## 6. Discussion

### 6.1 What worked
*(Fill in once §5 exists.)*

### 6.2 Limitations
- Small pilot N — results directional, not statistically powered.
- Grounding verifier's scheme-attribution is a lookback heuristic, not true
  NER — document as an open engineering limitation.
- Scheme RAG (the component most directly tied to the grounding-verifier
  contribution claim) is not in this pilot's live routing. If the paper's
  headline claim leans on grounding-verifier performance, either (a) report
  it as an offline/synthetic evaluation clearly labeled as such, or (b) run
  a small supplementary live evaluation before submission. Don't imply
  live-pilot validation of a feature that wasn't live in the pilot.
- The Negotiation agent's offer-amount extraction is a single-amount regex
  match — a message containing multiple numbers only captures the first.
  Acceptable for single-item bargaining; a real limitation for multi-item
  negotiation, worth stating rather than hiding.
- The Bangla calendar display is an explicit approximation (documented as
  such in the system itself), not verified against a specific panjika —
  state this plainly if the paper mentions the calendar feature at all;
  don't let a passing mention imply more precision than exists.
- The Flux Pro poster-generation integration's exact API request/response
  shape is unverified against live documentation as of writing — if
  discussed in the paper, state this as an open engineering item, not a
  settled integration.

### 6.3 Threats to validity
Self-selection in NGO-recruited participants; social-desirability bias;
short pilot duration relative to scheme-application timelines.

---

## 7. Conclusion
*(Write last, ~150 words, tied directly to whatever §5 actually shows.)*

---

## Appendix A — Interview guide
Reuse `docs/fieldwork.md` §3 verbatim.

## Appendix B — Consent forms
Reuse `docs/fieldwork.md` §2.1 and §2.2 verbatim.

## Appendix C — System prompts
Include, with English glosses:
- The anti-hallucination system prompt from `services/rag_service/pipeline.py`
- The ledger-extraction prompt from `services/orchestrator/nodes/ledger_node.py`
- **New**: the Negotiation agent's `COUNTER_REASON_SYSTEM` prompt from
  `services/orchestrator/nodes/negotiation_node.py`, specifically because
  its explicit "never write a number" instruction, paired with the
  code-level digit filter as a backstop, is a good illustration of
  defense-in-depth prompt design worth showing verbatim.

---

## Title Options

Three options depending on which contribution you want to lead with and
which venue you're targeting. All avoid the "multilingual" overclaim and
the vague "Intelligent" adjective from the originally proposed title.

**Option A — grounding-verifier-led, best fit for NLP4PI 2026 (NLP-mechanism audience):**
> *Catching "Right Scheme, Wrong Number": Citation-Grounded Government Scheme Eligibility in a Voice-First WhatsApp Assistant for Rural West Bengal*

**Option B — field-deployment-led, best fit for an ICTD/HCI4D venue (COMPASS-style, once 2027's CFP opens):**
> *Voice-First, Citation-Grounded Financial and Welfare Assistance for Low-Literacy Rural Women: A WhatsApp Field Deployment in West Bengal*
*(This was already your strongest prior draft title — kept here as Option B rather than discarded.)*

**Option C — broadest framing, if positioning the code-enforced-guardrail pattern as the paper's throughline across both RAG and non-RAG agents:**
> *Don't Trust the Model to State the Number: Structural Guard-Rails for LLM-Mediated Financial Information in a Voice-First WhatsApp Assistant*

Recommendation: **Option A for NLP4PI 2026** (live CFP, strong thematic
fit, and the grounding verifier is your most concrete, already-tested
artifact), **Option B held in reserve** for COMPASS 2027 or a broader
ICTD-audience submission of the same underlying work.

---

## Venue Targets — verified against live CFP pages, not search snippets

| Venue | Status as of this draft (July 2026) |
|---|---|
| **NLP4PI 2026** (5th workshop, co-located with EMNLP 2026, Budapest, Oct 24–29) | **CFP open now — primary target.** Explicitly welcomes work bridging NLP with HCI, social science, and NGOs. Confirm the exact submission deadline on the workshop's own Call for Papers 2026 page before finalizing a timeline — the workshop overview page confirms the CFP is live but the precise date should be pulled from the linked CFP page directly. |
| **ACM COMPASS 2026** | **Paper track submission closed** (was March 21, extended). Virtual conference July 27–31, 2026. Not viable for 2026 — retarget to **COMPASS 2027** once that CFP opens (check `compass.acm.org` in late 2026/early 2027). |
| **ACM IKDD CODS 2026** | CFP **not yet announced** as of this check (site states plans are "underway," dates to be confirmed). Watch, don't plan a submission timeline around it yet. |
| **EMNLP 2026 main conference** | ARR deadline (May 25, 2026) has passed. Too late for the main track this cycle; NLP4PI workshop above is the live path into the same event. |

**Realistic near-term plan given the above**: aim for NLP4PI 2026 as the
primary target. If the fieldwork timeline can't produce real §5 results in
time for that CFP, do not submit a paper without real numbers — hold for
COMPASS 2027 instead, and use the NLP4PI submission window as a forcing
function for finishing the pilot rather than skipping the venue if the
timeline is tight.

---

## Changelog

- **Retitled.** The previously proposed title ("Kotha-Khata: An Intelligent
  Multilingual WhatsApp Assistant Using Large Language Models and Document
  Processing Pipelines") was not used: "multilingual" overclaims (system is
  Bengali-first with one optional English-caption feature), "Document
  Processing Pipelines" describes a different system than the one built
  (voice-first, not document-first), and "Intelligent" is a non-specific
  filler adjective. Three alternatives are proposed above, none of which
  make either overclaim.
- **Added four real Related Work citations** found via literature search
  (ashabot/arXiv 2409.10913, WASHtsApp/arXiv 2411.02850, Sruti ASR
  benchmark/arXiv 2506.09653, "Beyond Semantics"/ACM FAccT 2025), plus one
  non-academic deployed comparator (EasyGov). None of these were present in
  any prior version of this draft.
- **Added §3.4**, generalizing the grounding-verifier's core principle to
  the newly-built Pricing and Negotiation agents — this is new work not
  covered in any earlier draft of this paper.
- **Added §3.6**, briefly covering the local product taxonomy and Bangla
  calendar additions — framed as minor supporting/localization work, not
  inflated into a main contribution.
- **Updated Limitations (§6.2)** with the specific, real limitations of the
  new agents (single-amount negotiation extraction, unverified Bangla
  calendar precision, unverified Flux Pro API shape) — consistent with this
  project's existing practice of stating known gaps plainly rather than
  glossing over them.
- **Replaced "verify current CFPs before submitting" placeholder language**
  with actually-verified, dated venue status: COMPASS 2026's paper track
  has closed (confirmed by fetching the live CFP page), NLP4PI 2026 is
  confirmed open and is now the recommended primary target, CODS 2026's CFP
  is confirmed not yet announced.
