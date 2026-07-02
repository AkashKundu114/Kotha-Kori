
from __future__ import annotations

from services.orchestrator.state import ConversationState
from services.orchestrator.model_router import route_completion, TaskCriticality

FINANCIAL_KEYWORDS = {"bikri", "বিক্রি", "kharach", "খরচ", "hisab", "হিসাব", "taka", "টাকা", "labh", "লাভ"}
REPORT_KEYWORDS = {"report", "রিপোর্ট", "maaser hisab", "মাসের হিসাব"}
MARKET_KEYWORDS = {"ki banabo", "কি বানাবো", "bazar", "বাজার", "chahida", "চাহিদা", "demand"}

INTENT_CLASSIFY_SYSTEM = """তুমি কোথা-খাতার ইনটেন্ট ক্লাসিফায়ার।
ব্যবহারকারীর বার্তা পড়ে নিচের একটি ক্যাটাগরি বেছে নাও এবং শুধু JSON ফেরত দাও:
{"feature": "LEDGER" | "LEDGER_REPORT" | "MARKET" | "UNKNOWN", "confidence": <0.0-1.0>}"""

async def classify_intent(state: ConversationState) -> dict:

    text = (state.get("raw_input_text") or state.get("raw_input_transcript") or "").lower()

    if any(k in text for k in REPORT_KEYWORDS):
        return {"active_feature": "LEDGER_REPORT", "trace": ["intent_router:keyword:LEDGER_REPORT"]}
    if any(k in text for k in FINANCIAL_KEYWORDS):
        return {"active_feature": "LEDGER", "trace": ["intent_router:keyword:LEDGER"]}
    if any(k in text for k in MARKET_KEYWORDS):
        return {"active_feature": "MARKET", "trace": ["intent_router:keyword:MARKET"]}

    if not text.strip():
        return {"active_feature": "IDLE", "trace": ["intent_router:empty_input"]}

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
