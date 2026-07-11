from __future__ import annotations

from services.orchestrator.state import ConversationState
from services.orchestrator.model_router import route_completion, TaskCriticality, ModelUnavailableError
from services.market_service.aggregator import block_sales_trend, classify_trend
from services.market_service.agmarknet_client import fetch_mandi_prices

PHRASING_SYSTEM = (
    "তুমি একজন বন্ধুত্বপূর্ণ বাজার পরামর্শদাতা, পশ্চিমবঙ্গের\n"
    "স্বনির্ভর গোষ্ঠীর মহিলাদের জন্য। দেওয়া তথ্যের ভিত্তিতে, সহজ কথ্য বাংলায়\n"
    "৩-৪ লাইনের একটি সংক্ষিপ্ত সাপ্তাহিক পরামর্শ লেখো। শুধুমাত্র দেওয়া তথ্য\n"
    "ব্যবহার করো, নতুন কোনো পণ্য বা সংখ্যা তৈরি করো না।"
)


async def market_predictor_node(state: ConversationState) -> dict:
    profile = state.get("user_profile") or {}
    block = profile.get("block")
    if not block:
        return {
            "outbound_messages": [{"type": "text", "body": "আপনার ব্লকের তথ্য নেই। অনুগ্রহ করে প্রোফাইল আপডেট করুন।"}],
            "trace": ["market_predictor_node:no_block"],
        }

    try:
        report = await _build_report(block)
    except Exception:
        return {
            "outbound_messages": [{"type": "text", "body": "বাজারের তথ্য আনতে সমস্যা হয়েছে। একটু পরে আবার চেষ্টা করুন।"}],
            "trace": ["market_predictor_node:build_report_failed"],
        }

    if not report["rising"] and not report["saturated"]:
        msg = "এই মুহূর্তে আপনার এলাকার জন্য যথেষ্ট তথ্য নেই। আরো ব্যবহারকারী যোগ হলে ভালো পরামর্শ দিতে পারব।"
        return {
            "market_report": report,
            "outbound_messages": [{"type": "text", "body": msg}],
            "trace": ["market_predictor_node:insufficient_data"],
        }

    try:
        phrased = await _phrase_report(report)
    except ModelUnavailableError:
        # Deterministic fallback — don't leave the user with nothing just because
        # the phrasing model is briefly down; the underlying trend data is still valid.
        phrased = _plain_fallback(report)

    return {
        "market_report": report,
        "outbound_messages": [{"type": "text", "body": phrased}],
        "trace": [f"market_predictor_node:done:rising={len(report['rising'])}:saturated={len(report['saturated'])}"],
    }


def _plain_fallback(report: dict) -> str:
    lines = []
    if report["rising"]:
        lines.append("📈 বেড়ে চলা পণ্য: " + ", ".join(report["rising"]))
    if report["saturated"]:
        lines.append("📉 বেশি সরবরাহ থাকা পণ্য: " + ", ".join(report["saturated"]))
    return "\n".join(lines)


async def _build_report(block: str) -> dict:
    trend_rows = await block_sales_trend(block)

    by_category: dict[str, list[dict]] = {}
    for row in trend_rows:
        by_category.setdefault(row["category"], []).append(row)

    rising, saturated = [], []
    for category, series in by_category.items():
        series_sorted = sorted(series, key=lambda r: r["week"] or "", reverse=True)
        trend = classify_trend(series_sorted)
        if trend == "rising":
            rising.append(category)
        elif trend == "saturated":
            saturated.append(category)

    try:
        mandi_prices = await fetch_mandi_prices(district=block)
    except Exception:
        mandi_prices = []  # optional external signal — never block the response on it

    return {"block": block, "rising": rising, "saturated": saturated, "mandi_prices": mandi_prices}


async def _phrase_report(report: dict) -> str:
    prompt = (
        f"বেড়ে চলা পণ্য: {', '.join(report['rising']) or 'নেই'}\n"
        f"বেশি সরবরাহ থাকা পণ্য: {', '.join(report['saturated']) or 'নেই'}\n"
        f"মান্ডি দাম তথ্য: {report['mandi_prices'][:5]}\n\n"
        "উপরের তথ্যের ভিত্তিতে সাপ্তাহিক বাজার পরামর্শ লেখো।"
    )
    result = await route_completion(
        system=PHRASING_SYSTEM, prompt=prompt, criticality=TaskCriticality.ROUTINE, confidence_floor=0.0
    )
    return result["text"].strip()
