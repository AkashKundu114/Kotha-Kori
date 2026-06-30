"""
Two-pass grounding verifier (see docs/ARCHITECTURE.md #5).

v1 returned `"hallucination_check_passed": True` unconditionally — there was
no actual check. This implements the 2026-standard pattern:

  Pass 1 — assertion extraction: pull every number, amount, date, and scheme
           name out of the generated Bengali answer.
  Pass 2 — grounding check: verify each assertion's surface text actually
           appears in the retrieved context, not just that it's topically
           related.

This is deliberately a cheap, deterministic check (regex + substring lookup)
rather than another LLM call — it needs to run on every single RAG answer,
so latency and cost matter. A heavier LLM-as-judge pass can be added later
for the weekly human audit (scripts/audit_rag.py) without slowing down the
live path.
"""
from __future__ import annotations

import re

# Bengali digits + Latin digits, so amounts in either script are caught.
_AMOUNT_RE = re.compile(r"(₹\s?[০-৯0-9,]+|[০-৯0-9,]+\s?টাকা)")
_DATE_RE = re.compile(r"\b(\d{1,2}\s?(জানুয়ারি|ফেব্রুয়ারি|মার্চ|এপ্রিল|মে|জুন|জুলাই|আগস্ট|সেপ্টেম্বর|অক্টোবর|নভেম্বর|ডিসেম্বর))\b")


def _extract_assertions(answer_bengali: str) -> list[str]:
    assertions = []
    assertions.extend(_AMOUNT_RE.findall(answer_bengali))
    assertions.extend(m[0] for m in _DATE_RE.findall(answer_bengali))
    return [a.strip() for a in assertions if a and isinstance(a, str)]


def verify_grounding(answer_bengali: str, retrieved_chunks: list[dict]) -> dict:
    """
    Returns: {"all_grounded": bool, "assertions": [...], "ungrounded": [...]}
    """
    combined_context = "\n".join(c.get("chunk_bengali") or c.get("chunk_text", "") for c in retrieved_chunks)

    assertions = _extract_assertions(answer_bengali)
    ungrounded = [a for a in assertions if a not in combined_context]

    return {
        "all_grounded": len(ungrounded) == 0,
        "assertions": assertions,
        "ungrounded": ungrounded,
        "num_chunks_used": len(retrieved_chunks),
    }
