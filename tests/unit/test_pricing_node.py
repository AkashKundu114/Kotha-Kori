import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from services.orchestrator.nodes.pricing_node import _recommend


def test_never_recommends_below_cost():
    result = _recommend(cost=100, margin=0.0, min_price=None, market_avg=None)
    assert result["recommended_price"] >= 100
    assert result["floor_price"] >= 100


def test_applies_preferred_margin_with_no_market_data():
    result = _recommend(cost=100, margin=0.30, min_price=None, market_avg=None)
    assert result["floor_price"] == 130.0
    assert result["recommended_price"] == 130.0


def test_minimum_price_overrides_a_lower_margin_based_floor():
    result = _recommend(cost=100, margin=0.10, min_price=180, market_avg=None)
    assert result["floor_price"] == 180.0


def test_market_average_pulls_price_up_but_stays_capped():
    result = _recommend(cost=100, margin=0.30, min_price=None, market_avg=1000)
    assert result["recommended_price"] <= 130.0 * 1.4
    assert result["recommended_price"] >= result["floor_price"]


def test_market_average_below_floor_is_ignored():
    result = _recommend(cost=100, margin=0.30, min_price=None, market_avg=110)
    assert result["recommended_price"] == result["floor_price"] == 130.0


def test_zero_cost_still_respects_minimum_price():
    result = _recommend(cost=0, margin=0.30, min_price=50, market_avg=None)
    assert result["floor_price"] == 50.0
