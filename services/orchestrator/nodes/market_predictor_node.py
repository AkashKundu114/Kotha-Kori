from __future__ import annotations

from datetime import date

from services.orchestrator.state import ConversationState
from services.orchestrator.model_router import route_completion, TaskCriticality, ModelUnavailableError
from services.market_service.aggregator import block_sales_trend, classify_trend
from services.market_service.agmarknet_client import fetch_mandi_prices
from shared.knowledge.context import get_context_for_agents
from shared.knowledge.crop_calendar import crops_at_harvest, crops_for_district
from shared.knowledge.dignity_guidelines import DIGNITY_RULES_BENGALI

PHRASING_SYSTEM = (
    "তুমি একজন বন্ধুত্বপূর্ণ বাজার পরামর্শদাতা, পশ্চিমবঙ্গের\n"
    "স্বনির্ভর গোষ্ঠীর মহিলাদের জন্য।\n\n"
    f"{DIGNITY_RULES_BENGALI}\n\n"
    "দেওয়া তথ্যের ভিত্তিতে, সহজ কথ্য বাংলায়\n"
    "৩-৪ লাইনের একটি সংক্ষিপ্ত সাপ্তাহিক পরামর্শ লেখো। শুধুমাত্র দেওয়া তথ্য\n"
    "ব্যবহার করো, নতুন কোনো পণ্য বা সংখ্যা তৈরি করো না। উৎসব বা মৌসুমি তথ্য থাকলে "
    "শুধু প্রাসঙ্গিক হলে উল্লেখ করো।"
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

    district = profile.get("district") or block
    knowledge = get_context_for_agents(month=date.today().month, block=block, district=district)
    report["knowledge"] = knowledge

    this_month_harvest = crops_at_harvest(date.today().month)
    if district:
        district_crops = {crop.slug for crop in crops_for_district(district)}
        if district_crops:
            this_month_harvest = [crop for crop in this_month_harvest if crop.slug in district_crops]
    report["crops_at_harvest"] = [
        {"slug": crop.slug, "name_bengali": crop.name_bengali, "note": crop.note_bengali}
        for crop in this_month_harvest
    ]

    if (
        not report["rising"]
        and not report["saturated"]
        and not knowledge["upcoming_festivals"]
        and not knowledge["upcoming_district_melas"]
        and not report["crops_at_harvest"]
    ):
        msg = "এই মুহূর্তে আপনার এলাকার জন্য যথেষ্ট তথ্য নেই। আরো ব্যবহারকারী যোগ হলে ভালো পরামর্শ দিতে পারব।"
        return {
            "market_report": report,
            "outbound_messages": [{"type": "text", "body": msg}],
            "trace": ["market_predictor_node:insufficient_data"],
        }

    try:
        phrased = await _phrase_report(report)
    except ModelUnavailableError:
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
    for festival in report.get("knowledge", {}).get("upcoming_festivals", []):
        lines.append(f"🎉 {festival['name_bengali']}: {festival['note']}")
    for mela in report.get("knowledge", {}).get("upcoming_district_melas", []):
        lines.append(f"🎪 {mela['name_bengali']} ({mela['district']}): {mela['note']}")
    for crop in report.get("crops_at_harvest", []):
        lines.append(f"🌾 {crop['name_bengali']}: {crop['note']}")
    return "\n".join(lines) or "এই মুহূর্তে বিশেষ কোনো পরামর্শ নেই।"


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
        mandi_prices = []

    return {"block": block, "rising": rising, "saturated": saturated, "mandi_prices": mandi_prices}


async def _phrase_report(report: dict) -> str:
    knowledge = report.get("knowledge", {})
    season = knowledge.get("season")
    festivals = knowledge.get("upcoming_festivals", [])
    melas = knowledge.get("upcoming_district_melas", [])
    crops = report.get("crops_at_harvest", [])
    prompt = (
        f"বেড়ে চলা পণ্য: {', '.join(report['rising']) or 'নেই'}\n"
        f"বেশি সরবরাহ থাকা পণ্য: {', '.join(report['saturated']) or 'নেই'}\n"
        f"মান্ডি দাম তথ্য: {report['mandi_prices'][:5]}\n"
        f"এই মাসের আবহাওয়া/মৌসুমি প্রবণতা: {season['weather_note'] if season else 'তথ্য নেই'}\n"
        f"আসন্ন উৎসব: {'; '.join(festival['name_bengali'] + ' - ' + festival['note'] for festival in festivals) or 'নেই'}\n"
        f"আসন্ন স্থানীয় মেলা: {'; '.join(mela['name_bengali'] + ' (' + mela['district'] + ')' for mela in melas) or 'নেই'}\n"
        f"এই মাসে যেসব ফসল উঠছে: {'; '.join(crop['name_bengali'] + ' - ' + crop['note'] for crop in crops) or 'নেই'}\n\n"
        "উপরের তথ্যের ভিত্তিতে সাপ্তাহিক বাজার পরামর্শ লেখো।"
    )
    result = await route_completion(
        system=PHRASING_SYSTEM, prompt=prompt, criticality=TaskCriticality.ROUTINE, confidence_floor=0.0
    )
    return result["text"].strip()
