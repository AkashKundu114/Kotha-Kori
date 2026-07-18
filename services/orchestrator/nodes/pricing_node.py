from __future__ import annotations

from sqlalchemy import select

from services.orchestrator.state import ConversationState
from services.orchestrator.model_router import (
    route_completion,
    TaskCriticality,
    AgentTier,
    ModelUnavailableError,
)
from services.market_service.aggregator import block_sales_trend
from shared.db.session import get_db_session
from shared.db.models import SellerProfile

PHRASING_SYSTEM = (
    "তুমি একজন বন্ধুত্বপূর্ণ মূল্য নির্ধারণ পরামর্শদাতা। দেওয়া সংখ্যার ভিত্তিতে\n"
    "২-৩ লাইনে সহজ বাংলায় ব্যাখ্যা করো কেন এই দাম প্রস্তাব করা হচ্ছে।\n"
    "শুধুমাত্র দেওয়া সংখ্যা ব্যবহার করো, নতুন কোনো দাম তৈরি করো না।"
)

NO_PROFILE_MSG = (
    "দাম ঠিক করতে আগে কিছু তথ্য দরকার: তৈরির খরচ কত, আর সর্বনিম্ন কত দামে বিক্রি করতে রাজি আছেন। "
    "যেমন বলুন: 'তৈরির খরচ ১৫০ টাকা, সর্বনিম্ন ২০০ টাকা'।"
)


def _recommend(cost: float, margin: float, min_price: float | None, market_avg: float | None) -> dict:
    """Deterministic — never LLM-generated. cost/margin/min_price come from
    the seller's own stated numbers; market_avg is an optional anchor, never
    a substitute for the seller's own floor. Mirrors the pattern in
    market_service/aggregator.py::classify_trend — numbers first, LLM only
    for phrasing the result afterward.

    Inputs are clamped to non-negative before use (red-team-agents-v2.md
    MED-1): a negative or missing production_cost with no minimum_price set
    would otherwise collapse the floor to <= 0, which negotiation_node would
    then treat as "accept any non-negative offer." Every caller of this
    function must additionally check `floor_price > 0` before proceeding —
    this function itself only guarantees non-negativity, not "usable."
    """
    cost = max(0.0, float(cost or 0))
    margin = max(0.0, float(margin or 0))
    min_price = max(0.0, float(min_price)) if min_price else None

    base = cost * (1 + margin)
    floor = max(base, min_price or 0, cost)

    if market_avg and market_avg > floor:


        recommended = min(market_avg * 0.95, floor * 1.4)
        recommended = max(recommended, floor)
    else:
        recommended = floor

    return {
        "recommended_price": round(recommended, 2),
        "floor_price": round(floor, 2),
        "market_avg": market_avg,
    }


async def pricing_node(state: ConversationState) -> dict:
    user_id = state.get("user_id")
    if not user_id:
        return {"outbound_messages": [{"type": "text", "body": NO_PROFILE_MSG}], "trace": ["pricing_node:no_user"]}

    async with get_db_session() as db:
        profile = (
            await db.execute(select(SellerProfile).where(SellerProfile.user_id == user_id))
        ).scalar_one_or_none()

    if not profile or not profile.production_cost:
        return {"outbound_messages": [{"type": "text", "body": NO_PROFILE_MSG}], "trace": ["pricing_node:no_profile"]}

    block = (state.get("user_profile") or {}).get("block")
    market_avg = None
    if block and profile.product_type:
        try:
            rows = await block_sales_trend(block)
            matches = [r for r in rows if profile.product_type in (r["category"] or "")]
            if matches:
                market_avg = sum(r["total_amount"] for r in matches) / len(matches)
        except Exception:
            pass

    calc = _recommend(
        cost=float(profile.production_cost),
        margin=float(profile.preferred_margin or 0.30),
        min_price=float(profile.minimum_price) if profile.minimum_price else None,
        market_avg=market_avg,
    )

    if calc["floor_price"] <= 0:



        return {"outbound_messages": [{"type": "text", "body": NO_PROFILE_MSG}], "trace": ["pricing_node:non_positive_floor"]}

    prompt = (
        f"তৈরির খরচ: ₹{profile.production_cost}\n"
        f"প্রস্তাবিত দাম: ₹{calc['recommended_price']}\n"
        f"সর্বনিম্ন দাম: ₹{calc['floor_price']}\n"
        f"বাজারের গড় দাম: {'₹' + str(round(market_avg)) if market_avg else 'তথ্য নেই'}"
    )
    try:
        result = await route_completion(
            system=PHRASING_SYSTEM,
            prompt=prompt,
            criticality=TaskCriticality.ROUTINE,
            tier=AgentTier.ADVANCED,
            confidence_floor=0.0,
        )
        explanation = result["text"].strip()
    except ModelUnavailableError:
        explanation = ""

    body = f"💰 প্রস্তাবিত দাম: ₹{calc['recommended_price']}\n(সর্বনিম্ন ₹{calc['floor_price']}-এর নিচে যাবেন না)"
    if explanation:
        body += f"\n\n{explanation}"

    return {
        "market_report": {"market_avg": market_avg} if market_avg else None,
        "outbound_messages": [{"type": "text", "body": body}],
        "trace": [f"pricing_node:recommended={calc['recommended_price']}"],
    }
