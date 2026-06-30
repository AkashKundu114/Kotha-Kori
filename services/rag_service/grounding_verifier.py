"""
Two-pass grounding verifier (see docs/ARCHITECTURE.md #5).

v1 returned `"hallucination_check_passed": True` unconditionally — there was
no actual check. v2 implemented the 2026-standard two-pass pattern:

  Pass 1 — assertion extraction: pull every number, amount, date, and scheme
           name out of the generated Bengali answer.
  Pass 2 — grounding check: verify each assertion's surface text actually
           appears in the retrieved context, not just that it's topically
           related.

v2.1 (this revision — see docs/INTERNSHIP_GUIDE.md Day 4-5, Option A):
the original Pass 2 concatenated every retrieved chunk into one blob before
searching for an assertion. That allows a "citation-shaped hallucination" to
slip through: if Scheme A's chunk genuinely says ₹1000 and a *different*
chunk for Scheme B happens to mention ₹2500, a generation that claims
"Scheme A gives ₹2500" was marked grounded — ₹2500 *is* present in the
combined context, just attached to the wrong scheme.

Fix: grounding is now checked per-chunk, and whenever the answer names a
scheme near an assertion, that assertion must be found within a chunk that
actually belongs to *that* scheme — not just somewhere in the retrieved set.

This is still deliberately a cheap, deterministic check (regex + substring
lookup + a small alias table) rather than another LLM call, since it runs on
every single RAG answer and latency/cost matter. A heavier LLM-as-judge pass
can be layered on top later for the weekly human audit (scripts/audit_rag.py)
without slowing down the live path.
"""
from __future__ import annotations

import re

# Bengali digits + Latin digits, so amounts in either script are caught.
_AMOUNT_RE = re.compile(r"(₹\s?[০-৯0-9,]+|[০-৯0-9,]+\s?টাকা)")
_DATE_RE = re.compile(r"\b(\d{1,2}\s?(জানুয়ারি|ফেব্রুয়ারি|মার্চ|এপ্রিল|মে|জুন|জুলাই|আগস্ট|সেপ্টেম্বর|অক্টোবর|নভেম্বর|ডিসেম্বর))\b")

# Bengali (and common Latin/abbreviated) surface forms a generated answer
# might use to name a scheme -> the canonical scheme_name stored on
# scheme_chunks/scheme_documents (see services/rag_service/pipeline.py,
# migrations/0002_hybrid_search.sql). Extend as new schemes are ingested
# (see data/schemes/raw/README.md for the launch list).
SCHEME_NAME_ALIASES: dict[str, str] = {
    "লক্ষ্মীর ভান্ডার": "Lakshmir Bhandar",
    "আনন্দধারা": "Anandadhara",
    "svskp": "SVSKP",
    "এসভিএসকেপি": "SVSKP",
    "কৃষক বন্ধু": "Krishak Bandhu",
    "wbssp": "WBSSP",
    "ডব্লিউবিএসএসপি": "WBSSP",
    "jaago": "JAAGO",
    "জাগো": "JAAGO",
    "কন্যাশ্রী": "Kanyashree",
    "রূপশ্রী": "Rupashree",
    "সবুজ সাথী": "Sabooj Sathi",
    "sabooj sathi": "Sabooj Sathi",
}

# How far back (characters) from an assertion to look for a scheme mention.
# The anti-hallucination system prompt instructs short sentences ("ছোট ছোট
# বাক্য"), so one sentence's worth of lookback is enough without accidentally
# picking up an unrelated scheme name mentioned two sentences earlier.
_SCHEME_LOOKBACK_CHARS = 60


def _extract_assertions(answer_bengali: str) -> list[tuple[str, int]]:
    """Returns [(assertion_text, start_index_in_answer), ...]."""
    assertions: list[tuple[str, int]] = []
    for m in _AMOUNT_RE.finditer(answer_bengali):
        assertions.append((m.group(1).strip(), m.start()))
    for m in _DATE_RE.finditer(answer_bengali):
        assertions.append((m.group(1).strip(), m.start()))
    return assertions


def _nearby_scheme(answer_bengali: str, assertion_start: int) -> str | None:
    """
    Look backward from the assertion for a known scheme-name alias, picking
    whichever alias occurs *closest* to the assertion (not just the first
    one in iteration order) — important for multi-scheme comparison answers
    like "X দেয় ₹1000, আর Y দেয় ₹2500", where an earlier mention of X must
    not shadow a closer, more relevant mention of Y for the second figure.
    """
    window_start = max(0, assertion_start - _SCHEME_LOOKBACK_CHARS)
    window = answer_bengali[window_start:assertion_start].lower()

    best_canonical: str | None = None
    best_pos = -1
    for alias, canonical in SCHEME_NAME_ALIASES.items():
        pos = window.rfind(alias.lower())
        if pos > best_pos:
            best_pos = pos
            best_canonical = canonical
    return best_canonical


def verify_grounding(answer_bengali: str, retrieved_chunks: list[dict]) -> dict:
    """
    Returns: {"all_grounded": bool, "assertions": [...], "ungrounded": [...]}

    Each assertion is checked against *individual* chunks (never one
    concatenated blob). If the answer names a scheme near the assertion, the
    assertion must be grounded specifically in a chunk belonging to that
    scheme; only assertions with no nearby scheme mention fall back to "found
    in any retrieved chunk."
    """
    assertions = _extract_assertions(answer_bengali)
    ungrounded: list[str] = []

    for assertion_text, start in assertions:
        claimed_scheme = _nearby_scheme(answer_bengali, start)
        grounded = False

        for chunk in retrieved_chunks:
            chunk_text = chunk.get("chunk_bengali") or chunk.get("chunk_text", "")
            if assertion_text not in chunk_text:
                continue

            if claimed_scheme is None:
                # No scheme could be identified near the assertion in the
                # answer text — fall back to "grounded somewhere in the
                # retrieved set," same behaviour as before this fix.
                grounded = True
                break

            chunk_scheme = (chunk.get("scheme_name") or "").strip().lower()
            if chunk_scheme == claimed_scheme.lower():
                grounded = True
                break
            # else: right number, found in retrieval, but in the WRONG
            # scheme's chunk — keep searching other chunks, don't trust this one.

        if not grounded:
            ungrounded.append(assertion_text)

    return {
        "all_grounded": len(ungrounded) == 0,
        "assertions": [a for a, _ in assertions],
        "ungrounded": ungrounded,
        "num_chunks_used": len(retrieved_chunks),
    }
