from __future__ import annotations

import re

from sqlalchemy import select

from services.orchestrator.state import ConversationState
from services.orchestrator.model_router import (
    route_completion,
    TaskCriticality,
    AgentTier,
    ModelUnavailableError,
)
from services.orchestrator.nodes.pricing_node import _recommend
from shared.db.session import get_db_session
from shared.db.models import SellerProfile

MAX_NEGOTIATION_TURNS = 4

NO_PROFILE_MSG = "দরদাম করতে আগে দাম ঠিক করা দরকার। 'দাম' লিখে আগে মূল্য জেনে নিন।"
NO_OFFER_MSG = "কাস্টমার কত দাম বলেছেন? যেমন লিখুন: 'কাস্টমার ৮০ টাকা বলেছে'।"
AFFIRMATIVE = {"হ্যাঁ", "হ্যা", "ha", "haan", "thik", "ঠিক", "রাজি", "ok", "okay", "👍"}

_AMOUNT_RE = re.compile(r"(₹\s?[০-৯0-9,]+|[০-৯0-9,]+\s?টাকা)")
_DIGIT_RE = re.compile(r"[০-৯0-9,]+")
_BENGALI_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

ACCEPT_SYSTEM = (
    "তুমি একজন বন্ধুত্বপূর্ণ বিক্রয় সহায়ক। কাস্টমারের প্রস্তাবিত দামে বিক্রেতা রাজি হয়েছেন।\n"
    "২ লাইনের মধ্যে উষ্ণভাবে নিশ্চিত করো এবং ধন্যবাদ জানাও।\n"
    "শুধুমাত্র দেওয়া দামটি উল্লেখ করো, নতুন কোনো সংখ্যা তৈরি করো না।"
)

COUNTER_SYSTEM = (
    "তুমি একজন বন্ধুত্বপূর্ণ বিক্রয় সহায়ক, বিক্রেতার পক্ষে দরদাম করছ।\n"
    "কাস্টমারের প্রস্তাব বিক্রেতার সর্বনিম্ন দামের চেয়ে কম, তাই বিনয়ীভাবে প্রত্যাখ্যান\n"
    "করে দেওয়া পাল্টা দামটি প্রস্তাব করো। ২-৩ লাইনের মধ্যে লেখো, পণ্যের মান বা\n"
    "খরচের একটা সংক্ষিপ্ত কারণ দাও। শুধুমাত্র দেওয়া পাল্টা দামটিই ব্যবহার করো —\n"
    "এর চেয়ে কম কোনো দাম কখনো লিখো না।"
)

ACCEPT_FALLBACK = "ঠিক আছে, ₹{amount} তে রাজি! ধন্যবাদ।"
COUNTER_FALLBACK = "দুঃখিত, ₹{offer} তে সম্ভব না। ₹{counter} হলে ঠিক আছে?"
HOLD_FIRM_FALLBACK = "দুঃখিত, এর থেকে কম দামে দেওয়া সম্ভব না। ₹{floor} হলে রাজি আছি।"


def _extract_amount(text: str) -> float | None:
    """Deterministic regex extraction — the same pattern as
    grounding_verifier.py's amount matching. No LLM is ever used to read
    the customer's proposed number; the LLM only ever sees an
    already-extracted amount and is asked to phrase a response, never to
    decide the outcome."""
    match = _AMOUNT_RE.search(text)
    if not match:
        return None
    digits = _DIGIT_RE.search(match.group(1))
    if not digits:
        return None
    try:
        return float(digits.group(0).translate(_BENGALI_DIGITS).replace(",", ""))
    except ValueError:
        return None


def _contains_amount_below(text: str, floor: float) -> bool:
    """Hard safety net: scans generated LLM phrasing for ANY rupee amount
    and flags it if it ever quotes below the floor. This check runs
    regardless of what the prompt instructed — it's a code-level guard,
    not a request to the model to police itself. If this ever fires, the
    LLM's output is discarded entirely in favor of a deterministic
    fallback line."""
    for match in _AMOUNT_RE.finditer(text):
        digits = _DIGIT_RE.search(match.group(1))
        if not digits:
            continue
        try:
            amt = float(digits.group(0).translate(_BENGALI_DIGITS).replace(",", ""))
        except ValueError:
            continue
        if amt < floor:
            return True
    return False


def _compute_counter_offer(floor: float, offer: float, turns: int) -> float:
    """Pure, deterministic, unit-testable. Never returns below floor —
    guaranteed by max(), not by convention. First turn holds firm at the
    floor itself; later turns split the gap between floor and the
    customer's latest offer, still never below floor."""
    if turns <= 1:
        return round(floor, 2)
    return round(max(floor, (floor + offer) / 2), 2)


async def negotiation_node(state: ConversationState) -> dict:
    text = (state.get("raw_input_text") or state.get("raw_input_transcript") or "").strip()
    pending = state.get("pending_negotiation")

    if not pending:
        return await _start_negotiation(state, text)
    return await _continue_negotiation(state, pending, text)


async def _load_floor(state: ConversationState) -> tuple[float, str] | None:
    user_id = state.get("user_id")
    if not user_id:
        return None
    async with get_db_session() as db:
        profile = (
            await db.execute(select(SellerProfile).where(SellerProfile.user_id == user_id))
        ).scalar_one_or_none()
    if not profile or not profile.production_cost:
        return None
    calc = _recommend(
        cost=float(profile.production_cost),
        margin=float(profile.preferred_margin or 0.30),
        min_price=float(profile.minimum_price) if profile.minimum_price else None,
        market_avg=None,
    )
    return calc["floor_price"], (profile.product_type or "পণ্য")


async def _start_negotiation(state: ConversationState, text: str) -> dict:
    loaded = await _load_floor(state)
    if loaded is None:
        return {"outbound_messages": [{"type": "text", "body": NO_PROFILE_MSG}], "trace": ["negotiation_node:no_profile"]}
    floor, product_type = loaded

    offer = _extract_amount(text)
    if offer is None:
        return {
            "pending_negotiation": {"floor_price": floor, "product_type": product_type, "turns": 0},
            "awaiting_negotiation": True,
            "outbound_messages": [{"type": "text", "body": NO_OFFER_MSG}],
            "trace": ["negotiation_node:awaiting_offer"],
        }
    return await _evaluate_offer(floor, product_type, offer, turns=1)


async def _continue_negotiation(state: ConversationState, pending: dict, text: str) -> dict:
    floor = pending["floor_price"]
    product_type = pending.get("product_type", "পণ্য")
    turns = pending.get("turns", 0) + 1

    if text.lower() in AFFIRMATIVE and pending.get("last_counter"):
        # Buyer accepted our previous counter-offer. Deterministic finalize —
        # no LLM call needed, no risk of the phrasing model inventing a
        # different number for a deal that's already settled.
        amount = pending["last_counter"]
        return {
            "pending_negotiation": None,
            "awaiting_negotiation": False,
            "outbound_messages": [{"type": "text", "body": ACCEPT_FALLBACK.format(amount=f"{amount:.0f}")}],
            "trace": [f"negotiation_node:finalized:{amount:.0f}"],
        }

    offer = _extract_amount(text)
    if offer is None:
        return {
            "pending_negotiation": pending,
            "awaiting_negotiation": True,
            "outbound_messages": [{"type": "text", "body": NO_OFFER_MSG}],
            "trace": [f"negotiation_node:awaiting_offer:turn={turns}"],
        }

    if turns > MAX_NEGOTIATION_TURNS:
        body = HOLD_FIRM_FALLBACK.format(floor=f"{floor:.0f}")
        return {
            "pending_negotiation": None,
            "awaiting_negotiation": False,
            "outbound_messages": [{"type": "text", "body": body}],
            "trace": [f"negotiation_node:max_turns_hold_firm:turn={turns}"],
        }

    return await _evaluate_offer(floor, product_type, offer, turns=turns)


async def _evaluate_offer(floor: float, product_type: str, offer: float, turns: int) -> dict:
    if offer >= floor:
        return await _accept(offer)
    return await _counter(floor, product_type, offer, turns)


async def _accept(offer: float) -> dict:
    """Deterministic outcome: `offer >= floor` is already verified in
    _evaluate_offer before this is ever called. The LLM is only asked to
    phrase a warm confirmation of an amount already decided in code."""
    prompt = f"সম্মত দাম: ₹{offer:.0f}"
    try:
        result = await route_completion(
            system=ACCEPT_SYSTEM, prompt=prompt, criticality=TaskCriticality.ROUTINE,
            tier=AgentTier.ADVANCED, confidence_floor=0.0,
        )
        body = result["text"].strip() or ACCEPT_FALLBACK.format(amount=f"{offer:.0f}")
    except ModelUnavailableError:
        body = ACCEPT_FALLBACK.format(amount=f"{offer:.0f}")

    # Safety net even on the acceptance path — the phrasing model shouldn't
    # ever quote a different, lower number than the one actually agreed.
    if _contains_amount_below(body, offer):
        body = ACCEPT_FALLBACK.format(amount=f"{offer:.0f}")

    return {
        "pending_negotiation": None,
        "awaiting_negotiation": False,
        "outbound_messages": [{"type": "text", "body": body}],
        "trace": [f"negotiation_node:accepted:{offer:.0f}"],
    }


async def _counter(floor: float, product_type: str, offer: float, turns: int) -> dict:
    """Offer is below floor. The counter number is computed in code by
    _compute_counter_offer — never generated by the LLM. The LLM is given
    that exact number and asked only to phrase it warmly."""
    counter_offer = _compute_counter_offer(floor, offer, turns)

    prompt = (
        f"পণ্য: {product_type}\n"
        f"কাস্টমারের প্রস্তাব: ₹{offer:.0f}\n"
        f"পাল্টা দাম (এই দামটিই ব্যবহার করো): ₹{counter_offer:.0f}"
    )
    try:
        result = await route_completion(
            system=COUNTER_SYSTEM, prompt=prompt, criticality=TaskCriticality.ROUTINE,
            tier=AgentTier.ADVANCED, confidence_floor=0.0,
        )
        body = result["text"].strip()
    except ModelUnavailableError:
        body = ""

    # Hard floor-guard: if the LLM ever quotes ANY amount below the actual
    # floor — hallucinated a discount, misread the prompt, whatever — its
    # entire output is discarded in favor of the deterministic fallback
    # line. This is a code-level check, independent of the prompt.
    if not body or _contains_amount_below(body, floor):
        body = COUNTER_FALLBACK.format(offer=f"{offer:.0f}", counter=f"{counter_offer:.0f}")

    return {
        "pending_negotiation": {
            "floor_price": floor,
            "product_type": product_type,
            "turns": turns,
            "last_counter": counter_offer,
        },
        "awaiting_negotiation": True,
        "outbound_messages": [{"type": "text", "body": body}],
        "trace": [f"negotiation_node:counter:{counter_offer:.0f}:turn={turns}"],
    }
