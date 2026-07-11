from __future__ import annotations

import httpx

from shared.config.settings import get_settings

# NOTE: exact resource ID / response schema not verified against the live
# data.gov.in API — verify before relying on this in production. Fails
# gracefully (returns []) on any error, which is by design: this is an
# optional enrichment signal, never a hard dependency for Feature 8.
_AGMARKNET_RESOURCE_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"


async def fetch_mandi_prices(district: str, commodity: str | None = None) -> list[dict]:
    s = get_settings()
    api_key = getattr(s, "data_gov_in_api_key", "") or ""
    if not api_key:
        return []

    params = {
        "api-key": api_key,
        "format": "json",
        "filters[state]": "West Bengal",
        "filters[district]": district,
        "limit": 50,
    }
    if commodity:
        params["filters[commodity]"] = commodity

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(_AGMARKNET_RESOURCE_URL, params=params)
            r.raise_for_status()
            body = r.json()
    except (httpx.HTTPError, ValueError):
        return []

    return _parse_response(body)


def _parse_response(body: dict) -> list[dict]:
    records = body.get("records", [])
    out = []
    for rec in records:
        try:
            out.append(
                {
                    "commodity": rec.get("commodity"),
                    "market": rec.get("market"),
                    "min_price": float(rec.get("min_price", 0) or 0),
                    "max_price": float(rec.get("max_price", 0) or 0),
                    "modal_price": float(rec.get("modal_price", 0) or 0),
                    "arrival_date": rec.get("arrival_date"),
                }
            )
        except (TypeError, ValueError):
            continue
    return out
