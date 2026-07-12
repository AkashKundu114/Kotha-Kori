from __future__ import annotations

import asyncio
import base64
import logging

import httpx

from shared.config.settings import get_settings

logger = logging.getLogger("flux_poster_client")

_TIMEOUT = 30.0
_POLL_INTERVAL_SECONDS = 1.5
_MAX_POLL_ATTEMPTS = 20


class FluxUnavailableError(Exception):
    pass


async def generate_poster_image(
    *,
    reference_image_bytes: bytes,
    product_name: str,
    ad_caption: str,
    price_min: float,
    price_max: float,
    shg_name: str = "",
) -> bytes:
    """Calls Flux Pro to generate a poster using the already-background-
    removed product photo as a reference image.

    OPEN VERIFICATION ITEM: the exact endpoint path, payload field names,
    and image-reference parameter below are a best-effort implementation
    against Flux Pro's documented async submit -> poll-by-id -> download
    -result-URL pattern, and have NOT been verified against live, current
    API docs. Confirm the request/response shape against your Flux Pro
    account's docs before relying on this in production — same caveat
    already flagged for Sarvam Vision in sarvam_client.py. If the shape is
    wrong, this raises FluxUnavailableError like any other failure and the
    caller falls back to the free Pillow tier — it does not silently ship
    a broken poster.
    """
    s = get_settings()
    if not s.flux_api_key:
        raise FluxUnavailableError("FLUX_API_KEY not configured")

    prompt = (
        f"Professional product advertisement poster for '{product_name}', "
        f"price range {price_min:.0f} to {price_max:.0f} rupees, "
        f"clean modern layout, bottom banner with Bengali caption: {ad_caption}. "
        + (f"Watermark text: {shg_name}. " if shg_name else "")
        + "Warm, inviting, small-business marketing style, high contrast text, "
        "based closely on the reference product photo provided."
    )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            submit_resp = await client.post(
                f"{s.flux_base_url}/v1/flux-pro-1.1",
                headers={"x-key": s.flux_api_key, "Content-Type": "application/json"},
                json={
                    "prompt": prompt,
                    "image_prompt": base64.b64encode(reference_image_bytes).decode(),
                    "width": 1024,
                    "height": 1280,
                },
            )
            submit_resp.raise_for_status()
            task_id = submit_resp.json().get("id")
            if not task_id:
                raise FluxUnavailableError("Flux Pro submit response missing task id")

            for _ in range(_MAX_POLL_ATTEMPTS):
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
                poll_resp = await client.get(
                    f"{s.flux_base_url}/v1/get_result",
                    headers={"x-key": s.flux_api_key},
                    params={"id": task_id},
                )
                poll_resp.raise_for_status()
                body = poll_resp.json()
                status = body.get("status")

                if status == "Ready":
                    image_url = (body.get("result") or {}).get("sample")
                    if not image_url:
                        raise FluxUnavailableError("Flux Pro reported Ready with no image URL")
                    image_resp = await client.get(image_url)
                    image_resp.raise_for_status()
                    return image_resp.content

                if status in ("Error", "Failed", "Content Moderated"):
                    raise FluxUnavailableError(f"Flux Pro generation failed: status={status}")

            raise FluxUnavailableError("Flux Pro polling exhausted without a Ready result")

    except FluxUnavailableError:
        raise
    except Exception as exc:
        raise FluxUnavailableError(str(exc)) from exc
