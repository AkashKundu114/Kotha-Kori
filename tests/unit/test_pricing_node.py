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
    # floor is 130; recommended should be pulled toward market but capped at floor*1.4
    assert result["recommended_price"] <= 130.0 * 1.4
    assert result["recommended_price"] >= result["floor_price"]


def test_market_average_below_floor_is_ignored():
    result = _recommend(cost=100, margin=0.30, min_price=None, market_avg=110)
    assert result["recommended_price"] == result["floor_price"] == 130.0


def test_zero_cost_still_respects_minimum_price():
    result = _recommend(cost=0, margin=0.30, min_price=50, market_avg=None)
    assert result["floor_price"] == 50.0


# --- MED-1 regression: docs/red-team-agents-v2.md ---------------------------
# A negative or zero production_cost with no minimum_price previously
# collapsed floor_price to <= 0, which negotiation_node would then treat as
# "accept any non-negative offer." _recommend now clamps inputs so the
# result is never negative; callers (pricing_node.pricing_node,
# negotiation_node._load_floor) are expected to explicitly refuse to
# proceed when floor_price <= 0 rather than silently negotiating from zero.

def test_negative_cost_never_produces_negative_floor():
    result = _recommend(cost=-500, margin=0.30, min_price=None, market_avg=None)
    assert result["floor_price"] >= 0


def test_zero_cost_with_no_minimum_price_gives_non_positive_floor():
    # This is the exact "insufficient data" case callers must reject rather
    # than silently proceed with — floor_price == 0 here is intentional
    # clamping, not a usable floor.
    result = _recommend(cost=0, margin=0.30, min_price=None, market_avg=None)
    assert result["floor_price"] == 0


def test_negative_margin_never_produces_a_floor_below_cost():
    result = _recommend(cost=100, margin=-0.9, min_price=None, market_avg=None)
    assert result["floor_price"] >= 100
