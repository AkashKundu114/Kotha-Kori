
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text

from shared.db.session import get_db_session

MIN_SAMPLE_SIZE = 5

async def block_sales_trend(block: str, weeks_back: int = 8) -> list[dict]:

    since = date.today() - timedelta(weeks=weeks_back)

    async with get_db_session() as db:
        rows = (
            await db.execute(
                text("""
                SELECT
                  le.category,
                  date_trunc('week', le.entry_date) AS week,
                  SUM(le.amount_inr) AS total_amount,
                  COUNT(DISTINCT le.user_id) AS distinct_sellers
                FROM ledger_entries le
                JOIN users u ON u.id = le.user_id
                WHERE u.block = :block
                  AND le.entry_type = 'INCOME'
                  AND le.entry_date >= :since
                GROUP BY le.category, week
                HAVING COUNT(DISTINCT le.user_id) >= :min_sample
                ORDER BY week DESC
            """),
                {"block": block, "since": since, "min_sample": MIN_SAMPLE_SIZE},
            )
        ).fetchall()

    return [
        {
            "category": r.category,
            "week": r.week.isoformat() if r.week else None,
            "total_amount": float(r.total_amount or 0),
            "distinct_sellers": r.distinct_sellers,
        }
        for r in rows
    ]

def classify_trend(weekly_series: list[dict]) -> str:

    if len(weekly_series) < 2:
        return "insufficient_data"
    recent = weekly_series[0]["total_amount"]
    prior = weekly_series[1]["total_amount"]
    if prior == 0:
        return "rising" if recent > 0 else "insufficient_data"
    change = (recent - prior) / prior
    if change > 0.15:
        return "rising"
    if change < -0.15:
        return "saturated"
    return "stable"
