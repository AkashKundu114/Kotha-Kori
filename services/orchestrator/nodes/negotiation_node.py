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

# Same domain-reasonable ceiling as ledger_confirm_node.MAX_REASONABLE_AMOUNT —
# anything above this for a single SHG micro-business item is almost
# certainly noise (or an attempt to break the floor comparison via a huge
# digit string that parses to `inf`; see red-team-agents-v2.md HIGH-1).
MAX_REASONABLE_OFFER = 500_000
MAX_REASON_CHARS = 200

NO_PROFILE_MSG = "দরদাম করতে আগে দাম ঠিক করা দরকার। 'দাম' লিখে আগে মূল্য জেনে নিন।"
NO_OFFER_MSG = "কাস্টমার কত দাম বলেছেন? যেমন লিখুন: 'কাস্টমার ৮০ টাকা বলেছে'।"
AFFIRMATIVE = {"হ্যাঁ", "হ্যা", "ha", "haan", "thik", "ঠিক", "রাজি", "ok", "okay", "👍"}

_AMOUNT_RE = re.compile(r"(₹\s?[০-৯0-9,]+|[০-৯0-9,]+\s?টাকা)")
_DIGIT_RE = re.compile(r"[০-৯0-9,]+")
_BENGALI_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# Reused from grounding_verifier.py's word-form-number handling: a reason
# fragment mentioning "পঞ্চাশ" (fifty) contains no digit *characters* at
# all, so a plain isdigit() scan misses it entirely — this was a real gap
# caught while re-testing this file's own fix (see
# docs/red-team-agents-v2.md CRIT-1). Any of these words appearing in a
# reason fragment is treated the same as a digit: discard the fragment.
_NUMBER_WORDS = {
    "শূন্য", "এক", "দুই", "তিন", "চার", "পাঁচ", "ছয়", "সাত", "আট", "নয়",
    "দশ", "এগারো", "বারো", "তেরো", "চৌদ্দ", "পনেরো", "ষোল", "সতেরো",
    "আঠারো", "উনিশ", "বিশ", "পঁচিশ", "ত্রিশ", "পঁয়ত্রিশ", "চল্লিশ",
    "পঁয়তাল্লিশ", "পঞ্চাশ", "ষাট", "সত্তর", "আশি", "নব্বই",
    "একশো", "দুইশো", "তিনশো", "চারশো", "পাঁচশো", "হাজার", "লাখ",
}
_NUMBER_WORD_RE = re.compile("|".join(re.escape(w) for w in _NUMBER_WORDS))

# NOTE ON DESIGN — read before touching this file:
#
# The LLM (Sarvam-105B) is NEVER asked to write a price, in either the
# accept or counter-offer flow. It is only ever asked for a short,
# digit-free justification sentence, and _mentions_a_number() discards that
# entire fragment outright if it contains so much as one digit. The actual
# quoted number is always interpolated by code, from a value that was
# already computed deterministically (never below the seller's floor by
# construction — see _compute_counter_offer). This is a structural
# guarantee, not a pattern-matching filter.
#
# An earlier version of this file tried to catch a bad LLM-generated price
# by scanning its output for ₹/টাকা patterns after the fact. That approach
# was a blocklist and was proven to miss bare digits with no currency
# marker, the Bengali Taka sign (৳, distinct from ₹), romanized "taka", and
# spelled-out number words — see docs/red-team-agents-v2.md CRIT-1 for the
# reproduction. Do not reintroduce "let the LLM write the number, then try
# to catch it if it's wrong" — the number must never originate from the LLM
# in the first place.

ACCEPT_REASON_SYSTEM = (
    "তুমি একজন বন্ধুত্বপূর্ণ বিক্রয় সহায়ক। একটি লেনদেন সম্পন্ন হয়েছে।\n"
    "শুধুমাত্র একটি ছোট, উষ্ণ ধন্যবাদসূচক বাক্য লেখো (সর্বোচ্চ ১ লাইন)।\n"
    "কঠোর নিয়ম: কোনো সংখ্যা, অংক, বা দাম কখনো লিখো না — শুধু কৃতজ্ঞতা প্রকাশ করো। "
    "দামটি অন্য কোথাও যোগ করা হবে, তোমাকে সেটা লিখতে হবে না।"
)

COUNTER_REASON_SYSTEM = (
    "তুমি একজন বন্ধুত্বপূর্ণ বিক্রয় সহায়ক, বিক্রেতার পক্ষে দরদাম করছ।\n"
    "কাস্টমারের প্রস্তাব বিক্রেতার সর্বনিম্ন দামের চেয়ে কম। একটি ছোট, বিনয়ী কারণ\n"
    "লেখো কেন এত কমে দেওয়া যাচ্ছে না (পণ্যের মান বা তৈরির খরচের কথা বলে), সর্বোচ্চ ১-২ লাইন।\n"
    "কঠোর নিয়ম: কোনো সংখ্যা, অংক, বা দাম কখনো লিখো না — শুধু কারণটা ব্যাখ্যা করো। "
    "পাল্টা দামটি অন্য কোথাও যোগ করা হবে, তোমাকে সেটা লিখতে হবে না।"
)


def _extract_amount(text: str) -> float | None:
    """Deterministic regex extraction of the customer's proposed amount —
    the same pattern as grounding_verifier.py's amount matching. Validates
    finite + in-range before returning, so a very long digit string can't
    parse to `inf`/overflow and silently satisfy `offer >= floor` for any
    floor (see red-team-agents-v2.md HIGH-1 — this was a real, reproduced
    bug in an earlier version of this file)."""
    match = _AMOUNT_RE.search(text)
    if not match:
        return None
    digits = _DIGIT_RE.search(match.group(1))
    if not digits:
        return None
    try:
        value = float(digits.group(0).translate(_BENGALI_DIGITS).replace(",", ""))
    except (ValueError, OverflowError):
        return None
    if value != value or value in (float("inf"), float("-inf")):  # NaN / inf guard
        return None
    if value < 0 or value > MAX_REASONABLE_OFFER:
        return None
    return value


def _mentions_a_number(text: str) -> bool:
    """The LLM's reason fragment must never contain a price — see the
    module docstring above. A legitimate justification ('ভালো মানের
    কারণে') has no reason to contain a digit OR a spelled-out number word,
    so this filter can be maximally aggressive with zero false-positive
    cost: discarding an occasional harmless fragment is strictly
    preferable to ever letting a number the model invented reach the
    customer. Checks both digit characters (Bengali or Latin) and the
    spelled-out Bengali number words in _NUMBER_WORDS — a digit-only check
    misses "পঞ্চাশ" (fifty) entirely, since it contains no digit glyphs at
    all (see docs/red-team-agents-v2.md CRIT-1)."""
    if any(ch.isdigit() or "০" <= ch <= "৯" for ch in text):
        return True
    return bool(_NUMBER_WORD_RE.search(text))


def _compute_counter_offer(floor: float, offer: float, turns: int) -> float:
    """Pure, deterministic, unit-testable. Never returns below floor —
    guaranteed by max(), not by convention. First turn holds firm at the
    floor itself; later turns split the gap between floor and the
    customer's latest offer, still never below floor."""
    if turns <= 1:
        return round(floor, 2)
    return round(max(floor, (floor + offer) / 2), 2)


async def _generate_reason(system: str, prompt: str) -> str:
    """Shared helper for both the accept and counter flows. Returns "" (not
    an error) on any failure or policy violation — an empty reason just
    means the outbound message has no extra sentence, never a missing or
    wrong price, since the price is never sourced from here."""
    try:
        result = await route_completion(
            system=system, prompt=prompt, criticality=TaskCriticality.ROUTINE,
            tier=AgentTier.ADVANCED, confidence_floor=0.0,
        )
        candidate = result["text"].strip()
    except ModelUnavailableError:
        return ""

    if not candidate or len(candidate) > MAX_REASON_CHARS or _mentions_a_number(candidate):
        return ""
    return candidate


async def negotiation_node(state: ConversationState) -> dict:
    text = (state.get("raw_input_text") or state.get("raw_input_transcript") or "").strip()
    pending = state.get("pending_negotiation")

    if not pending:
        return await _start_negotiation(state, text)
    return await _continue_negotiation(state, pending, text)


async def _load_floor(state: ConversationState) -> tuple[float, str] | None:
    """Returns None if no valid, positive floor can be established — this
    includes the MED-1 data-integrity case (bad/missing production_cost
    collapsing the floor to <= 0), which is treated identically to "no
    profile set up yet" rather than silently negotiating from a ₹0 floor."""
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
    if calc["floor_price"] <= 0:
        return None
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
        # Buyer accepted our previous counter-offer. Fully deterministic
        # finalize — no LLM call for the number, optional digit-free thank-you.
        amount = pending["last_counter"]
        reason = await _generate_reason(ACCEPT_REASON_SYSTEM, "লেনদেন সম্পন্ন হয়েছে।")
        body = f"✅ ঠিক আছে, ₹{amount:.0f} তে রাজি!" + (f" {reason}" if reason else "")
        return {
            "pending_negotiation": None,
            "awaiting_negotiation": False,
            "outbound_messages": [{"type": "text", "body": body}],
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
        body = f"দুঃখিত, এর থেকে কম দামে দেওয়া সম্ভব না। ₹{floor:.0f} হলে রাজি আছি।"
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
    _evaluate_offer before this is ever called. The number in the outbound
    message is always `offer`, interpolated by code — the LLM only ever
    supplies an optional, digit-free thank-you sentence."""
    reason = await _generate_reason(ACCEPT_REASON_SYSTEM, f"সম্মত দাম চূড়ান্ত হয়েছে।")
    body = f"✅ ঠিক আছে, ₹{offer:.0f} তে রাজি! ধন্যবাদ।" if not reason else f"✅ ঠিক আছে, ₹{offer:.0f} তে রাজি! {reason}"
    return {
        "pending_negotiation": None,
        "awaiting_negotiation": False,
        "outbound_messages": [{"type": "text", "body": body}],
        "trace": [f"negotiation_node:accepted:{offer:.0f}"],
    }


async def _counter(floor: float, product_type: str, offer: float, turns: int) -> dict:
    """Offer is below floor. counter_offer is computed by
    _compute_counter_offer — a pure function that structurally cannot
    return below floor. The LLM never sees this number as something it
    should write; it only ever supplies an optional, digit-free reason,
    which is validated by _generate_reason before use."""
    counter_offer = _compute_counter_offer(floor, offer, turns)

    reason = await _generate_reason(
        COUNTER_REASON_SYSTEM,
        f"পণ্য: {product_type}\nকাস্টমারের প্রস্তাব বিক্রেতার সর্বনিম্ন দামের চেয়ে কম।",
    )
    body = f"দুঃখিত, ₹{offer:.0f} তে সম্ভব না। ₹{counter_offer:.0f} হলে ঠিক আছে?"
    if reason:
        body += f" {reason}"

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
