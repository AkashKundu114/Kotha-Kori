import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from services.market_service.aggregator import classify_trend, MIN_SAMPLE_SIZE


def test_rising_trend():
    series = [{"week": "2026-06-29", "total_amount": 5000}, {"week": "2026-06-22", "total_amount": 3000}]
    assert classify_trend(series) == "rising"


def test_saturated_trend():
    series = [{"week": "2026-06-29", "total_amount": 2000}, {"week": "2026-06-22", "total_amount": 4000}]
    assert classify_trend(series) == "saturated"


def test_stable_trend():
    series = [{"week": "2026-06-29", "total_amount": 4100}, {"week": "2026-06-22", "total_amount": 4000}]
    assert classify_trend(series) == "stable"


def test_insufficient_data_single_week():
    assert classify_trend([{"week": "2026-06-29", "total_amount": 1000}]) == "insufficient_data"


def test_insufficient_data_empty():
    assert classify_trend([]) == "insufficient_data"


def test_k_anonymity_floor_is_five():
    # This is a privacy guarantee, not a tunable knob — regression-guard it.
    assert MIN_SAMPLE_SIZE == 5
