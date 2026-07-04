"""
Demo 2 - Market Trend Classifier
No API key needed.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.market_service.aggregator import classify_trend


def show(title, series):
    print(title)
    for row in series:
        print(f"  week={row['week']}  total_amount=₹{row['total_amount']}")
    print("Trend:", classify_trend(series))
    print()


show(
    "Case 1: Papad sales rising",
    [
        {"week": "2026-06-29", "total_amount": 5000},
        {"week": "2026-06-22", "total_amount": 3000},
    ],
)

show(
    "Case 2: Kantha embroidery oversupplied",
    [
        {"week": "2026-06-29", "total_amount": 2000},
        {"week": "2026-06-22", "total_amount": 4000},
    ],
)

show(
    "Case 3: Poultry sales stable",
    [
        {"week": "2026-06-29", "total_amount": 4100},
        {"week": "2026-06-22", "total_amount": 4000},
    ],
)

show(
    "Case 4: Not enough data yet",
    [{"week": "2026-06-29", "total_amount": 1000}],
)
