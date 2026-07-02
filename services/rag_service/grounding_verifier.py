from __future__ import annotations

import re

_AMOUNT_RE = re.compile(r"(₹\s?[০-৯0-9,]+|[০-৯0-9,]+\s?টাকা)")
_DATE_RE = re.compile(r"\b(\d{1,2}\s?(জানুয়ারি|ফেব্রুয়ারি|মার্চ|এপ্রিল|মে|জুন|জুলাই|আগস্ট|সেপ্টেম্বর|অক্টোবর|নভেম্বর|ডিসেম্বর))\b")

_NUMBER_WORDS = {
    "এক": 1, "দুই": 2, "তিন": 3, "চার": 4, "পাঁচ": 5,
    "দশ": 10, "পনেরো": 15, "বিশ": 20, "পঁচিশ": 25, "ত্রিশ": 30,
    "পঞ্চাশ": 50, "একশো": 100, "দুইশো": 200, "তিনশো": 300,
    "পাঁচশো": 500, "হাজার": 1000,
}
_WORD_AMOUNT_RE = re.compile(
    r"(?:" + "|".join(re.escape(w) for w in _NUMBER_WORDS) + r")"
    r"(?:\s+(?:" + "|".join(re.escape(w) for w in _NUMBER_WORDS) + r"))*"
    r"\s+টাকা"
)

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

_SCHEME_LOOKBACK_CHARS = 60

def _extract_assertions(answer_bengali: str) -> list[tuple[str, int]]:

    assertions: list[tuple[str, int]] = []
    for m in _AMOUNT_RE.finditer(answer_bengali):
        assertions.append((m.group(1).strip(), m.start()))
    for m in _DATE_RE.finditer(answer_bengali):
        assertions.append((m.group(1).strip(), m.start()))
    for m in _WORD_AMOUNT_RE.finditer(answer_bengali):

        assertions.append((m.group(0).strip(), m.start()))
    return assertions

def _nearby_scheme(answer_bengali: str, assertion_start: int) -> str | None:

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

                grounded = True
                break

            chunk_scheme = (chunk.get("scheme_name") or "").strip().lower()
            if chunk_scheme == claimed_scheme.lower():
                grounded = True
                break

        if not grounded:
            ungrounded.append(assertion_text)

    return {
        "all_grounded": len(ungrounded) == 0,
        "assertions": [a for a, _ in assertions],
        "ungrounded": ungrounded,
        "num_chunks_used": len(retrieved_chunks),
    }
