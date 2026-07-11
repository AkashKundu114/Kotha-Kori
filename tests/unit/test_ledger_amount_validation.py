import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from services.orchestrator.nodes.ledger_confirm_node import _validate_amount, MAX_REASONABLE_AMOUNT


def test_normal_amount_passes():
    assert _validate_amount(300.0) == 300.0


def test_negative_amount_rejected():
    assert _validate_amount(-50.0) is None


def test_nan_rejected():
    assert _validate_amount(float("nan")) is None


def test_infinity_rejected():
    assert _validate_amount(float("inf")) is None
    assert _validate_amount(float("-inf")) is None


def test_over_max_reasonable_amount_rejected():
    assert _validate_amount(MAX_REASONABLE_AMOUNT + 1) is None


def test_at_max_reasonable_amount_accepted():
    assert _validate_amount(MAX_REASONABLE_AMOUNT) == MAX_REASONABLE_AMOUNT


def test_rounds_to_two_decimal_places():
    assert _validate_amount(199.999) == 200.0
