from __future__ import annotations

import asyncio
import base64
import logging
import re

import httpx

from shared.config.settings import get_settings

logger = logging.getLogger("flux_poster_client")

_REQUEST_TIMEOUT = 15.0          # per-HTTP-call timeout (was 30s — see LOW-2)
_POLL_INTERVAL_SECONDS = 1.5
_MAX_POLL_ATTEMPTS = 20
_OVERALL_BUDGET_SECONDS = 60.0   # hard ceiling regardless of internal retry/poll bookkeeping

# Same class of cap as shared/whatsapp/media.py's MAX_AUDIO_BYTES/MAX_IMAGE_BYTES
# — see docs/red-team-agents-v2.md MED-2. A generated poster has no
# legitimate reason to be larger than this.
_MAX_RESULT_IMAGE_BYTES = 8 * 1024 * 1024

_MAX_PROMPT_FIELD_CHARS = 200
_TAG_RE = re.compile(r"<[^>]*>")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


class FluxUnavailableError(Exception):
    """Raised on any Flux Pro failure (missing key, HTTP error, timeout,
    generation failure, oversized/invalid result, or polling exhausted).
    Callers treat this exactly like SarvamUnavailableError /
    ModelUnavailableError elsewhere — fall through to the free Pillow
    fallback in poster_composer.py, never crash."""


def _clean_prompt_field(value: str, max_len: int = _MAX_PROMPT_FIELD_CHARS) -> str:
    """Sanitizes AI-generated text (product_name/ad_caption, ultimately
    derived from a vision model reading a user-submitted photo) before it's
    embedded in the Flux Pro prompt. Same defense-in-depth idea as
    pdf_service/generator.py's _clean() — strip tags/control characters and
    cap length, since this text was never meant to be arbitrary instruction
    text. See docs/red-team-agents-v2.md LOW-1."""
    if not value:
        return ""
    value = _TAG_RE.sub("", value)
    value = _CONTROL_CHARS_RE.sub("", value)
    return value.strip()[:max_len]


async def _download_result_image(client: httpx.AsyncClient, image_url: str, headers: dict) -> bytes:
    """Streaming download with a hard size cap and an https-only check —
    see docs/red-team-agents-v2.md MED-2. Aborts as soon as the cap is
    exceeded rather than buffering an unbounded response into memory."""
    if not image_url.lower().startswith("https://"):
        raise FluxUnavailableError(f"refusing non-https result URL: {image_url!r}")

    chunks: list[bytes] = []
    total = 0
    async with client.stream("GET", image_url, headers=headers) as resp:
        resp.raise_for_status()
        async for chunk in resp.aiter_bytes():
            total += len(chunk)
            if total > _MAX_RESULT_IMAGE_BYTES:
                raise FluxUnavailableError(
                    f"Flux Pro result image exceeded {_MAX_RESULT_IMAGE_BYTES} bytes cap"
                )
            chunks.append(chunk)
    return b"".join(chunks)


async def _generate_poster_image_impl(
    *,
    reference_image_bytes: bytes,
    product_name: str,
    ad_caption: str,
    price_min: float,
    price_max: float,
    shg_name: str,
) -> bytes:
    s = get_settings()
    if not s.flux_api_key:
        raise FluxUnavailableError("FLUX_API_KEY not configured")
    if not s.flux_base_url.lower().startswith("https://"):
        raise FluxUnavailableError("FLUX_BASE_URL must be https — refusing to send API key over an insecure scheme")

    product_name = _clean_prompt_field(product_name)
    ad_caption = _clean_prompt_field(ad_caption, max_len=400)
    shg_name = _clean_prompt_field(shg_name, max_len=100)

    prompt = (
        f"Professional product advertisement poster for '{product_name}', "
        f"price range {price_min:.0f} to {price_max:.0f} rupees, "
        f"clean modern layout, bottom banner with Bengali caption: {ad_caption}. "
        + (f"Watermark text: {shg_name}. " if shg_name else "")
        + "Warm, inviting, small-business marketing style, high contrast text, "
        "based closely on the reference product photo provided."
    )

    headers = {"x-key": s.flux_api_key, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        submit_resp = await client.post(
            f"{s.flux_base_url}/v1/flux-pro-1.1",
            headers=headers,
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
                return await _download_result_image(client, image_url, headers={"x-key": s.flux_api_key})

            if status in ("Error", "Failed", "Content Moderated"):
                raise FluxUnavailableError(f"Flux Pro generation failed: status={status}")

        raise FluxUnavailableError("Flux Pro polling exhausted without a Ready result")


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
    against Flux Pro's documented async submit -> poll-by-id -> download-
    result-URL pattern, and have NOT been verified against live, current
    API docs. Confirm the request/response shape against your Flux Pro
    account's docs before relying on this in production — same caveat
    already flagged for Sarvam Vision in sarvam_client.py. If the shape is
    wrong, this raises FluxUnavailableError like any other failure and the
    caller falls back to the free Pillow tier — it does not silently ship
    a broken poster.

    Wrapped in an outer wall-clock ceiling (docs/red-team-agents-v2.md
    LOW-2) independent of the internal poll/retry bookkeeping, so a
    slow-but-not-cleanly-failing Flux endpoint can never tie up a Celery
    worker slot beyond a fixed budget.
    """
    try:
        return await asyncio.wait_for(
            _generate_poster_image_impl(
                reference_image_bytes=reference_image_bytes,
                product_name=product_name,
                ad_caption=ad_caption,
                price_min=price_min,
                price_max=price_max,
                shg_name=shg_name,
            ),
            timeout=_OVERALL_BUDGET_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise FluxUnavailableError(f"Flux Pro exceeded overall {_OVERALL_BUDGET_SECONDS}s budget") from exc
    except FluxUnavailableError:
        raise
    except Exception as exc:
        raise FluxUnavailableError(str(exc)) from exc
