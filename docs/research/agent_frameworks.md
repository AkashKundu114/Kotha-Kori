# Research Notes (2026) Behind the v2 Architecture

Summarized findings from a review of current production guidance, used to justify
the decisions in `docs/engineering/ARCHITECTURE.md`. Not exhaustive — re-verify before relying on
specific numbers, providers change pricing/quality often.

## Indic voice/LLM providers
- Sarvam AI (Peak XV/Lightspeed-backed) focuses specifically on low-latency
  conversational voice pipelines for Indian languages; independent STT benchmarks
  in 2026 place it ahead of Bhashini on accuracy for production call/voice-note use,
  at a real but modest per-minute cost.
- Bhashini (GoI, MeitY) remains the strongest **free** option, especially for
  bootstrapped/NGO-style projects, and covers all 22 scheduled languages — best used
  as a cost-control fallback tier, not the latency-critical primary path.
- Self-hosted open Indic ASR/TTS (AI4Bharat, IndicTTS) is real and production-viable,
  but the engineering cost (GPU serving, streaming latency optimization) is
  significant — consistent with the original plan's instinct to fine-tune Whisper,
  just repositioned as the *final* fallback tier rather than the *only* alternative
  to a free government API.

## Agent orchestration frameworks
- LangGraph is the most-cited framework for **stateful, branching, human-in-the-loop**
  conversational agents in 2026 production surveys (used at Klarna, Replit, Elastic).
  Its explicit typed-state-graph model with built-in Postgres/SQLite checkpointing is
  precisely the gap in the original keyword-router + Celery-task design.
- Alternatives considered: CrewAI (better for role-based multi-agent crews, not this
  shape of problem), LlamaIndex Workflows (better when the system is mostly
  document-pipeline shaped), Anthropic's Claude Agent SDK (best if going all-in on
  Claude as the only model — we deliberately want cascading, so LangGraph's
  model-agnostic design fits better).

## RAG hallucination prevention
- 2026 guidance converges on: hybrid retrieval (BM25/full-text + vector, fused),
  per-claim citation, and an explicit **second verification pass** — extract
  assertions from the generated answer, then check each one is actually supported
  by retrieved context — rather than trusting the generation step alone.
- RAGAS-style metrics (Faithfulness, Answer Relevancy, Context Precision/Recall) are
  the standard way to numerically track RAG quality over time; targets cited in
  2026 production guides: Faithfulness > 0.9, Answer Relevancy > 0.85,
  Context Precision > 0.8. Wire these into `scripts/audit_rag.py` once real traffic
  exists.

## WhatsApp automation maturity
- The WhatsApp automation market in 2026 distinguishes three tiers: simple Flows
  (decision-tree forms), chatbots, and full agentic AI. The mature pattern is to use
  Flows for *structured* data collection and reserve agentic/LLM processing for
  genuinely open-ended input (voice notes, free text) — matches decision #3 above.
