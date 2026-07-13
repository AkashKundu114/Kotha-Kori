import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from services.orchestrator.nodes.negotiation_node import (
    _extract_amount,
    _mentions_a_number,
    _compute_counter_offer,
    MAX_REASONABLE_OFFER,
)


# --- _extract_amount: normal cases -----------------------------------------

def test_extract_amount_digit_form():
    assert _extract_amount("কাস্টমার ৮০ টাকা বলেছে") == 80.0


def test_extract_amount_rupee_symbol_form():
    assert _extract_amount("সে ₹150 দিতে চায়") == 150.0


def test_extract_amount_with_comma():
    assert _extract_amount("₹1,200 দেবে বলেছে") == 1200.0


def test_extract_amount_none_when_no_number():
    assert _extract_amount("সে রাজি না") is None


# --- _extract_amount: HIGH-1 regression (unbounded input -> inf) -----------
# docs/red-team-agents-v2.md HIGH-1: a long digit string used to parse to
# float('inf'), which unconditionally satisfied `offer >= floor` for ANY
# floor. These lock in the fix.

def test_extract_amount_rejects_very_long_digit_string():
    attack = "৯" * 400 + " টাকা দিচ্ছি"
    assert _extract_amount(attack) is None


def test_extract_amount_rejects_value_above_ceiling():
    assert _extract_amount(f"{MAX_REASONABLE_OFFER + 1} টাকা দিচ্ছি") is None


def test_extract_amount_accepts_value_at_ceiling():
    assert _extract_amount(f"{int(MAX_REASONABLE_OFFER)} টাকা দিচ্ছি") == MAX_REASONABLE_OFFER


# --- _mentions_a_number: CRIT-1 regression suite ----------------------------
# docs/red-team-agents-v2.md CRIT-1: the original amount-scanning safety net
# was a bypassable blocklist. These are the exact phrasings that bypassed it,
# now checked against the replacement (_mentions_a_number, used to gate
# whether an LLM-generated "reason" fragment is allowed through at all).

def test_mentions_a_number_catches_bare_digit_no_currency_marker():
    assert _mentions_a_number("ঠিক আছে, ৫০ হলে চলবে, রাজি!") is True


def test_mentions_a_number_catches_bengali_taka_sign():
    assert _mentions_a_number("ঠিক আছে, ৳50 হলে চলবে") is True


def test_mentions_a_number_catches_romanized_taka():
    assert _mentions_a_number("ok, 50 taka thik ache") is True


def test_mentions_a_number_catches_spelled_out_number_word():
    # This specific case slipped through an earlier version of this fix
    # that only checked digit characters — "পঞ্চাশ" (fifty) has none.
    assert _mentions_a_number("পঞ্চাশ টাকা হলে রাজি") is True


def test_mentions_a_number_catches_spelled_out_hundred():
    assert _mentions_a_number("একশো টাকায় দিতে পারি") is True


def test_mentions_a_number_catches_spelled_number_without_currency_word():
    assert _mentions_a_number("মাত্র দুইশো তে নিয়ে নিন") is True


def test_mentions_a_number_false_for_genuinely_number_free_text():
    clean = "ভালো মানের হাতের কাজ, তাই এই দামে দেওয়া মুশকিল।"
    assert _mentions_a_number(clean) is False


# --- _compute_counter_offer: never below floor ------------------------------

def test_counter_offer_first_turn_holds_at_floor():
    assert _compute_counter_offer(floor=200, offer=100, turns=1) == 200.0


def test_counter_offer_never_below_floor_with_very_low_offer():
    assert _compute_counter_offer(floor=500, offer=10, turns=2) >= 500.0


def test_counter_offer_never_below_floor_with_offer_near_floor():
    assert _compute_counter_offer(floor=200, offer=199, turns=3) >= 200.0
