import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from services.orchestrator.nodes.negotiation_node import (
    _extract_amount,
    _contains_amount_below,
    _compute_counter_offer,
)


def test_extract_amount_digit_form():
    assert _extract_amount("কাস্টমার ৮০ টাকা বলেছে") == 80.0


def test_extract_amount_rupee_symbol_form():
    assert _extract_amount("সে ₹150 দিতে চায়") == 150.0


def test_extract_amount_with_comma():
    assert _extract_amount("₹1,200 দেবে বলেছে") == 1200.0


def test_extract_amount_none_when_no_number():
    assert _extract_amount("সে রাজি না") is None


def test_contains_amount_below_true_when_lower_amount_present():
    assert _contains_amount_below("ঠিক আছে ₹80 তে দিচ্ছি", floor=100) is True


def test_contains_amount_below_false_when_amount_at_or_above_floor():
    assert _contains_amount_below("ঠিক আছে ₹120 তে দিচ্ছি", floor=100) is False


def test_contains_amount_below_false_when_no_amount_present():
    assert _contains_amount_below("ধন্যবাদ, যোগাযোগ রাখুন", floor=100) is False


def test_counter_offer_first_turn_holds_at_floor():
    assert _compute_counter_offer(floor=200, offer=100, turns=1) == 200.0


def test_counter_offer_later_turn_splits_gap_but_never_below_floor():
    result = _compute_counter_offer(floor=200, offer=180, turns=2)
    assert result >= 200.0


def test_counter_offer_never_below_floor_even_with_high_offer_near_floor():
    # offer already close to floor — split should still clamp at/above floor
    result = _compute_counter_offer(floor=200, offer=199, turns=3)
    assert result >= 200.0


def test_counter_offer_never_below_floor_with_very_low_offer():
    result = _compute_counter_offer(floor=500, offer=10, turns=2)
    assert result >= 500.0
