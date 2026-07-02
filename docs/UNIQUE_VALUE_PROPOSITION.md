# What's Actually Unique Here vs. Generic AI Tools

Written for your research paper's "related work / positioning" section and
for explaining the project to your mentor or a conference audience — every
claim below is tied to a specific mechanism in the code, not a marketing
line.

## vs. ChatGPT / Gemini / a generic LLM chat app
A generic assistant requires literacy (to type or read) and an app install
or account, and it will **confidently answer a government scheme
eligibility question wrong** with no mechanism to catch it. Three concrete
differences:
1. **Zero install, zero literacy required** — WhatsApp voice notes in, voice
   or short text out. The target user never has to read a text interface if
   she doesn't want to (`preferred_modality` in the user model).
2. **Grounding verification, not just RAG** — `grounding_verifier.py`
   catches the specific failure mode of "real number, wrong scheme" that a
   plain RAG-over-documents chatbot has no mechanism to catch, because it
   never checks *which* retrieved chunk a generated claim actually came from.
3. **Per-user adaptive routing** — `ledger_node.py`'s personalized confidence
   floor tightens the reliability threshold for a specific user if the
   system has been wrong for them before. A generic chatbot applies the same
   model to everyone regardless of its own track record with them.

## vs. a no-code WhatsApp bot builder (Wati, Twilio + a prompt, etc.)
These give you a chat interface on WhatsApp; they don't give you:
- A **cascaded model router** that only spends Claude-tier cost on calls
  where a wrong answer has real financial/eligibility consequence
  (`model_router.py`'s `TaskCriticality` split) — a no-code builder is
  either all-cheap-model (unreliable on the calls that matter) or
  all-expensive-model (unsustainable at volume for a free social-impact
  tool).
- **Structured, auditable financial state** — `ledger_entries` with
  `is_corrected`/`extracted_by` provenance, feeding an actual
  bank-submittable PDF (`pdf_service/generator.py`), not just a chat
  transcript.
- **k-anonymized aggregate market intelligence** — `aggregator.py`'s
  `MIN_SAMPLE_SIZE` floor is a privacy mechanism a generic bot builder has
  no concept of, because it has no notion of "this data point represents a
  vulnerable individual's income."

## vs. a generic background-removal / product-photo app (Remove.bg, etc.)
Those do step one of Feature 3 and stop. This system chains that into:
vision-model product identification → Bengali caption generation calibrated
to a rural SHG audience → a price-range suggestion → delivery on the channel
the user already has open, with zero additional app switching. The value
isn't the background removal — that part is commodity — it's that it's the
*last* step in a chain a generic tool doesn't complete, in the one place the
user actually needs it to land.

## vs. a generic financial-literacy chatbot for underbanked populations
This is the closest comparison and worth being honest about, since it's what
reviewers will compare you against. The genuine differentiator is
**outcome-grounded evaluation** — the `CatalogCreation.user_reported_sale_resulted`
field and similar follow-up tracking (see `USER_MODEL_AND_RESEARCH.md`'s
metrics table) measure whether a bank actually accepted the generated
document or a sale actually resulted, not just whether the chatbot's NLP
metrics looked good in a lab eval. Most published systems in this space
report task accuracy, not real-world uptake — if your pilot data shows even
a handful of real bank-accepted PDFs, that's a stronger empirical claim than
most comparable papers make.

## The honest caveat
None of the individual techniques here (cascade routing, grounding
verification, k-anonymized aggregation) are novel in isolation — all are
documented 2026 practice (`docs/research/agent_frameworks.md`). The
contribution is the **combination, applied to a specific underserved
population, with field-validated outcome data** — that's a legitimate
systems/deployment paper, not a claim of new ML methods. Frame it that way;
claiming algorithmic novelty you don't have will hurt you with reviewers
more than an honestly-scoped deployment paper will.
