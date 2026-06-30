"""
Intent routing node — the LangGraph replacement for the old keyword-set
if/elif chain in services/gateway/router.py.

Kept deliberately simple (fast keyword pass first, LLM fallback second) —
the win over v1 isn't "smarter routing", it's that this is now one node in an
explicit graph with typed state, instead of a router function that fires off
disconnected Celery tasks each managing their own slice of Redis state.
"""
from __future__ import annotations

from services.orchestrator.state import ConversationState
from services.orchestrator.model_router import route_completion, TaskCriticality

FINANCIAL_KEYWORDS = {"bikri", "বিক্রি", "kharach", "খরচ", "hisab", "হিসাব", "taka", "টাকা", "labh", "লাভ"}
SCHEME_KEYWORDS = {"prakalpa", "প্রকল্প", "yojana", "যোজনা", "lakshmir", "লক্ষ্মীর", "svskp", "jaago", "anandadhara"}
MEETING_KEYWORDS = {"sobha", "সভা", "mishon", "মিটিং", "boisak", "বৈঠক", "hajira", "হাজিরা"}
TRAINING_KEYWORDS = {"shikhte", "শিখতে", "training", "course", "কোর্স"}
AGRI_KEYWORDS = {"chasha", "চাষ", "khet", "ক্ষেত", "gach", "গাছ", "rog", "রোগ", "murgi", "মুরগি"}

INTENT_CLASSIFY_SYSTEM = """তুমি কোথা-খাতার ইনটেন্ট ক্লাসিফায়ার।
ব্যবহারকারীর বার্তা পড়ে নিচের একটি ক্যাটাগরি বেছে নাও এবং শুধু JSON ফেরত দাও:
{"feature": "LEDGER" | "SCHEME_RAG" | "MEETING" | "TRAINING" | "AGRI" | "UNKNOWN",
 "confidence": <0.0-1.0>}"""


async def classify_intent(state: ConversationState) -> dict:
    text = (state.get("raw_input_text") or state.get("raw_input_transcript") or "").lower()

    if any(k in text for k in FINANCIAL_KEYWORDS):
        return {"active_feature": "LEDGER", "trace": ["intent_router:keyword:LEDGER"]}
    if any(k in text for k in SCHEME_KEYWORDS):
        return {"active_feature": "SCHEME_RAG", "trace": ["intent_router:keyword:SCHEME_RAG"]}
    if any(k in text for k in MEETING_KEYWORDS):
        return {"active_feature": "MEETING", "trace": ["intent_router:keyword:MEETING"]}
    if any(k in text for k in TRAINING_KEYWORDS):
        return {"active_feature": "TRAINING", "trace": ["intent_router:keyword:TRAINING"]}
    if any(k in text for k in AGRI_KEYWORDS):
        return {"active_feature": "AGRI", "trace": ["intent_router:keyword:AGRI"]}

    if not text.strip():
        return {"active_feature": "IDLE", "trace": ["intent_router:empty_input"]}

    # No keyword hit — fall back to the LLM. This is a ROUTINE task: cheap local
    # model first, escalate to Claude only if it's not confident. Misrouting a
    # message is annoying, not dangerous, so it doesn't need SAFETY_CRITICAL.
    result = await route_completion(
        system=INTENT_CLASSIFY_SYSTEM,
        prompt=text,
        criticality=TaskCriticality.ROUTINE,
    )
    import json

    try:
        parsed = json.loads(result["text"])
        feature = parsed.get("feature", "UNKNOWN")
    except (json.JSONDecodeError, TypeError):
        feature = "UNKNOWN"

    return {
        "active_feature": feature if feature != "UNKNOWN" else "IDLE",
        "trace": [f"intent_router:llm:{result['model_used']}:{feature}"],
    }
