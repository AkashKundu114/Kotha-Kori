# Internship Onboarding Guide — Kotha-Khata v2

Welcome. This guide gets you from zero to your first merged PR. Read it in order —
don't skip to "Day 3" before doing Day 1, the later steps assume you've actually
run the system once.

## Before Day 1 — accounts you'll need

You won't get all of these on day one — ask your team lead which you actually need
for your first task. Don't block on getting everything at once.

1. **GitHub access** to this repo.
2. **Anthropic API key** (for Claude calls in `model_router.py` — a small free/dev
   credit is usually enough to get started; ask your lead about a shared dev key).
3. **Sarvam AI API key** (sarvam.ai — has a free tier for development).
4. **Bhashini API key** (free, but registration takes a few days — apply on day 1
   even if you don't need it immediately: `dhruva-api.bhashini.gov.in`).
5. A **Meta test WhatsApp Business number** — your lead will likely already have
   one shared for the dev team; you don't need your own.

## Day 1 — Read before you touch code

1. `README.md` — repo map.
2. `docs/ARCHITECTURE.md` — **the most important file in this repo.** It explains
   every major design decision and what problem it solves. If you're about to
   write code that contradicts this document, stop and ask why first.
3. `docs/PRD.md` — who you're building for (read the personas — Sunita, Rina — and
   keep them in mind; this is not a generic chatbot project).
4. `docs/research/agent_frameworks.md` — the evidence behind decision #1-#6 in
   ARCHITECTURE.md, if you want to go deeper.

## Day 2 — Get it running locally

```bash
git clone <repo-url> && cd kotha-khata-v2
cp .env.example .env
# Fill in at minimum: ANTHROPIC_API_KEY, DATABASE_URL stays default for local dev.
# Leave SARVAM_API_KEY / BHASHINI_API_KEY blank for now — you can develop
# against text messages without them; voice testing comes later.

make setup     # postgres, redis up; migrations run
make dev       # full stack via docker compose
```

Verify:
```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

Run the test suite (this should pass with zero config — it doesn't touch the network):
```bash
make test
```

## Day 3 — Trace a message through the system by hand

This is the single most useful exercise for understanding the architecture.

1. Open `services/orchestrator/graph.py`. Find `build_graph()`. Draw it on paper:
   boxes for nodes, arrows for edges. This is the entire conversation logic of
   the bot — if you understand this file, you understand the system.
2. Open `services/orchestrator/nodes/intent_router.py`. Trace what happens to the
   text `"আজ ৩০০ টাকা পাপড় বিক্রি"` step by step — which keyword set catches it,
   what state field gets set, where the graph routes next.
3. Open `services/orchestrator/nodes/ledger_node.py`. Trace the same message
   through extraction. Notice it never calls Claude directly — it calls
   `route_completion()` from `model_router.py`. Open that file and understand
   the cascade logic (local model first, escalate on low confidence).
4. Send that exact message to your local bot (via the Meta test number, or by
   POSTing a synthetic webhook payload to `/webhook/whatsapp` — ask your lead for
   a sample payload if one isn't in `tests/fixtures/` yet) and watch it in the
   Langfuse UI at `localhost:3000`.

## Day 4-5 — Your first task

Pick **one** of these, in order of how much they teach you about the codebase:

### Option A (recommended first task): extend the grounding verifier
`tests/unit/test_grounding_verifier.py` already has a comment pointing at the
gap: the current verifier checks that a number/date appears *somewhere* in the
retrieved context, but not that it's attached to the *right scheme*. Read
`services/rag_service/grounding_verifier.py`, then:
1. Write a failing test that demonstrates a "right number, wrong scheme" hallucination
   slipping through.
2. Fix `verify_grounding()` to catch it (hint: you'll need to check that the
   assertion appears within the *same chunk*, not just somewhere across all
   concatenated context).
3. Open a PR. This is small, well-scoped, and touches the most safety-critical
   part of the system — a great way to build trust fast.

### Option B: add a new orchestrator node
Pick an unimplemented feature stub (`MEETING`, `AGRI`, `CATALOG`, `TRAINING` — see
the `_route_after_intent()` TODO comment in `graph.py`). Look at
`services/orchestrator/nodes/ledger_node.py` as your template: read input from
state, call `model_router.route_completion()` with the right `TaskCriticality`,
return a partial state update with `outbound_messages`. Register it in
`graph.py`. Reference the full conversation spec for that feature in
`docs/APP_FLOW.md` (carried over from v1 — still accurate for *what* each
feature should do, even though *how* it's wired changed).

### Option C: wire up a WhatsApp Flow handler
`services/gateway/whatsapp_flows/scheme_eligibility_flow.json` exists but nothing
in the orchestrator consumes its `complete` payload yet (it arrives as a
`message_type == "interactive"` message — see `_dispatch_to_orchestrator()` in
`services/gateway/main.py`). Build a deterministic eligibility rule-engine node
(no LLM needed — see `docs/APP_FLOW.md` §5 for the actual eligibility rules) that
consumes this payload and returns a checklist.

## Conventions to follow

- **Every new orchestrator node is a pure function**: `(ConversationState) -> dict`
  (a partial state update). Don't reach into Redis or the DB directly from a node
  except through `shared/db/session.py` — keeps nodes testable without a live graph.
- **Any LLM call goes through `model_router.route_completion()`**, never a direct
  `anthropic.Anthropic()` or Ollama call from inside a node. This keeps the
  cost/criticality decision in one auditable place.
- **Anything that could produce a wrong scheme amount, eligibility verdict, or
  financial figure shown to a user must pass through the grounding verifier (RAG)
  or be deterministic (rule engines), never a bare LLM generation.**
- Run `make lint` before opening a PR.

## Who to ask

Don't sit stuck for more than ~30 minutes on a setup/environment problem — ask in
the team channel. Sitting stuck on understanding *why* a design decision was made
is what `docs/ARCHITECTURE.md` is for — read it again before asking "why is it
built this way," the answer is probably already written down.
