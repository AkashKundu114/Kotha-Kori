# Kotha-Khata (কথা-খাতা) — Portfolio Case Study

**Voice-first financial & market intelligence infrastructure for rural West Bengal SHG women, delivered entirely through WhatsApp.**

> One-line summary for a resume: *"Designed and shipped a LangGraph-orchestrated, cascade-routed AI system serving low-literacy users over WhatsApp — including a citation-grounded RAG pipeline with a novel per-scheme hallucination verifier, and a cost-aware LLM router that cut per-message inference cost by routing on task criticality rather than task type."*

---

## 1. The problem, in one paragraph

Rural Self-Help Group (SHG) women in West Bengal run real micro-businesses — pickle production, Kantha embroidery, poultry — but have no bookkeeping, don't know which government schemes they qualify for, and have no way to market their products beyond word-of-mouth. They have WhatsApp. They often can't reliably read or write. Generic AI chatbots assume literacy and app adoption this population doesn't have, and — more dangerously — will confidently hallucinate a wrong government scheme amount with no mechanism to catch it. This system is a domain-locked, safety-first alternative: voice in, structured financial records and verified information out.

## 2. What I actually built (scope-honest)

| Feature | Status | What it does |
|---|---|---|
| **Voice-Ledger** | Built, tested | Bengali voice note → structured income/expense entry → confirm/correct loop → bank-submittable PDF |
| **Catalog Creator** | Built, tested | Product photo → background removal → vision-model product ID → Bengali sales caption → price suggestion |
| **Market Predictor** | Built, tested | k-anonymized aggregation of ledger sales data by block → rising/saturated product trend classification |
| **Scheme RAG (hallucination-guarded)** | Built, code-complete, not in V3 pilot routing | Government scheme eligibility Q&A with a two-pass grounding verifier |

This honesty matters for an interview: I scoped a v1 PRD with 8 features down to 3 for a 2-week pilot, explicitly deferring the rest — and documented *why*, not just *what*. That decision-making trail is itself part of the portfolio.

## 3. Technical decisions worth discussing in an interview

### 3.1 Orchestration: LangGraph over a keyword router + scattered Celery tasks
The original architecture dispatched on hand-written keyword sets into independent Celery tasks that read/wrote Redis session state by convention — nothing enforced a valid state transition, and debugging meant reading Redis by hand. I replaced this with a single `StateGraph` (`services/orchestrator/graph.py`): typed conversation state, Postgres-checkpointed, every turn resumable and replayable. Celery is kept only as the execution substrate so a slow node doesn't block WhatsApp's 20-second webhook ack — LangGraph runs *inside* a Celery task, not instead of it.

**Interview talking point:** the difference between "orchestration framework" and "state machine you can actually debug at 2am." A Postgres checkpointer means I can replay any user's exact conversation state, not guess at it from logs.

### 3.2 Cost-aware LLM routing by task criticality, not task type
Most cascade systems route cheap-vs-expensive model by *task type* (e.g., "extraction is always cheap, generation is always expensive"). I routed by **consequence of being wrong**: government scheme eligibility answers always go to Claude (wrong answer = real financial harm to someone who can't cross-check it), while routine ledger extraction goes to a self-hosted fine-tuned Qwen2.5-7B first, escalating to Claude only if the local model's self-reported confidence drops below a threshold — and that threshold is **personalized per user** based on their historical correction rate (`ledger_node.py::_personalized_confidence_floor`). A user the system has been wrong for before gets a stricter bar before trusting the cheap model on her again.

**Interview talking point:** this is a genuinely non-obvious routing signal — most production cascade systems don't condition on per-user reliability history. Worth a small ablation if this becomes a paper (fixed floor vs. adaptive floor, measured against correction rate).

### 3.3 RAG hallucination prevention: catching "right number, wrong scheme"
The naive grounding check (does this claimed number appear *anywhere* in the retrieved context?) has a specific, dangerous failure mode: if Scheme A's chunk says ₹1000 and a different retrieved chunk for Scheme B mentions ₹2500, a generation claiming "Scheme A gives ₹2500" passes a naive check — ₹2500 *is* in the context, just attached to the wrong scheme. I rewrote `grounding_verifier.py` to check grounding **per-chunk**, matching each numeric assertion to the scheme named nearest to it in the generated answer via an alias table, so cross-scheme hallucinations are caught instead of silently passing. Also extended assertion extraction to catch Bengali **word-form** numbers ("এক হাজার টাকা"), not just digit forms — the fine-tuned model's own training data teaches it to sometimes generate numbers as words, which would otherwise bypass a digit-only regex entirely.

**Interview talking point:** this is a self-found regression class ("citation-shaped hallucination") with a concrete reproduction, a fix, and 9 unit tests (`tests/unit/test_grounding_verifier.py`) covering the exact swapped-amount and word-form cases. Good artifact to walk through live in a technical interview — it's small, self-contained, and demonstrates adversarial thinking about your own system.

### 3.4 Security: two independent audit passes, with real findings
I ran a structured security audit (`docs/security.md`) and a second red-team pass specifically looking for what the first missed (`docs/red-team.md`). The second pass found things the first didn't: Redis/Postgres/Ollama bound to `0.0.0.0` with no auth (single `redis-cli FLUSHALL` = total outage + re-opens an already-"fixed" replay vulnerability), a webhook HMAC verification bug using the wrong secret entirely (verify-token instead of app-secret — meaning it either silently drops all real traffic or is trivially forgeable), and an SSRF/injection primitive in the PDF generator (Jinja2 autoescape was off, and WeasyPrint fetches remote resources it finds in rendered HTML — meaning a malicious "product category" string spoken into a voice note could make the PDF service issue outbound requests to internal infra, e.g. the cloud metadata endpoint).

**Interview talking point:** the discipline of a *second, adversarial* pass finding real CRIT-severity issues the first structured pass missed is a stronger signal than either audit alone. Walk through CRIT-2 (SSRF via unescaped LLM-generated content into a PDF renderer) — it's a good example of a vulnerability class (LLM output → templated document renderer with network access) that's easy to miss because it doesn't look like classic XSS.

### 3.5 Privacy-by-construction in the market intelligence feature
`aggregator.py`'s `MIN_SAMPLE_SIZE = 5` floor means no block/product-category trend is ever reported unless at least 5 distinct sellers contributed to it — a k-anonymity mechanism enforced at the query level (`HAVING COUNT(DISTINCT le.user_id) >= :min_sample`), not as an afterthought filter. This exists specifically because each data point represents a vulnerable individual's income, and the docstring says so.

## 4. Metrics and evaluation methodology (what I measured, not just what I built)

| Metric | Method | Target |
|---|---|---|
| STT word error rate, by dialect | Weekly automated eval against labeled sample set | ≤ 92% WER on rural Bengali |
| Ledger extraction accuracy | Correction-rate proxy + manual audit of 100 samples | ≥ 88% |
| RAG hallucination rate | Grounding-verifier output logged per query, weekly human audit of 50-sample | Zero tolerated in manual audit |
| Real-world outcome: PDF bank-acceptance | Day-14/30 WhatsApp follow-up survey | Tracked, not assumed |
| Real-world outcome: scheme checklist → application submitted | Same survey pattern | Tracked via `scheme_interactions.user_confirmed_applied` |

I deliberately instrumented **outcome-grounded evaluation** — not just NLP metrics — because most published systems in this space report task accuracy, not real-world uptake. If even a handful of pilot users actually got a bank-accepted PDF or a submitted scheme application, that's a stronger empirical claim than most comparable systems make. See `docs/research.md` for the full plan.

## 5. What I'd say if asked "what would you do differently"

- I'd add mTLS/service-to-service auth before any move to a shared Kubernetes namespace — the current network-isolation-via-docker-compose boundary is a deliberate, documented, pilot-scale tradeoff, not an oversight (see `security.md` H5).
- The scheme-name-detection in the grounding verifier is a fixed backward-lookback window, not real coreference resolution — it misses the case where the scheme name appears *after* the amount in a sentence. Documented as a known limitation with a concrete follow-up (`architecture.md` §7.1).
- `ledger_correction_rate` is read for personalization but the recompute job (nightly, from `is_corrected` flags) was never written — a good example of a "the read path is done, the write path isn't" gap I flagged explicitly rather than let it look silently complete.

## 6. Repository structure (for a quick technical skim)

```
services/orchestrator/        LangGraph state machine — start here
  graph.py                    the single source of truth for what features exist
  model_router.py             criticality-based Claude/Qwen cascade
  nodes/                      one pure function per feature
services/rag_service/
  grounding_verifier.py       the hallucination-catching logic (see §3.3)
services/market_service/
  aggregator.py                k-anonymized trend aggregation
docs/security.md               structured audit
docs/red-team.md               adversarial audit
docs/research.md               user model + evaluation plan
docs/fieldwork.md              field research materials
tests/unit/test_grounding_verifier.py   9 tests, good first thing to walk through
```

## 7. License & positioning note

AGPLv3 — a deliberate choice for a publicly-funded, social-impact network service (the network-copyleft clause matters here: if someone forks this and runs it as a hosted service, they owe the modified source back to their users). This is itself worth a sentence in an interview: showing you understand *why* a license choice fits a project's mission, not just picking MIT by default.
