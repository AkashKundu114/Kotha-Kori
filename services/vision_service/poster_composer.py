from __future__ import annotations

import asyncio
import io
import logging
import os

from PIL import Image, ImageDraw, ImageFont

from shared.config.settings import get_settings
from services.vision_service.flux_poster_client import generate_poster_image, FluxUnavailableError

logger = logging.getLogger("poster_composer")

_BANNER_HEIGHT_RATIO = 0.22  # bottom banner takes ~22% of the poster height
_PADDING = 24
_BANNER_BG = (26, 82, 118, 235)  # semi-opaque brand navy
_TEXT_COLOR = (255, 255, 255)
_PRICE_COLOR = (247, 202, 24)


def _load_font(size: int) -> ImageFont.FreeTypeFont | None:
    s = get_settings()
    path = s.bengali_font_path
    if not path or not os.path.exists(path):
        return None
    try:
        return ImageFont.truetype(path, size=size)
    except Exception:
        return None


def compose_poster(
    processed_image_bytes: bytes,
    *,
    product_name: str,
    ad_caption: str,
    price_min: float,
    price_max: float,
    shg_name: str = "",
) -> bytes | None:
    """Free, local, Pillow-based poster composite — the permanent fallback
    tier regardless of Flux Pro's availability. Composites a bottom banner
    (product name, price, short ad caption, SHG watermark) onto the
    already-background-removed product photo. Returns None (never raises)
    if the Bengali font asset isn't available — caller falls back to
    sending the plain photo with captions as separate messages, so a
    missing font is a UX downgrade, never a crash."""
    title_font = _load_font(42)
    body_font = _load_font(28)
    price_font = _load_font(36)
    if title_font is None or body_font is None or price_font is None:
        logger.warning("Bengali font not available at settings.bengali_font_path — skipping poster composite")
        return None

    try:
        product_img = Image.open(io.BytesIO(processed_image_bytes)).convert("RGB")
        w, h = product_img.size
        banner_h = int(h * _BANNER_HEIGHT_RATIO)

        poster = Image.new("RGB", (w, h + banner_h), (255, 255, 255))
        poster.paste(product_img, (0, 0))

        banner = Image.new("RGBA", (w, banner_h), _BANNER_BG)
        draw = ImageDraw.Draw(banner)

        y = _PADDING
        draw.text((_PADDING, y), _truncate(product_name, 40), font=title_font, fill=_TEXT_COLOR)
        y += title_font.size + 8

        price_text = f"₹{price_min:.0f} – ₹{price_max:.0f}"
        draw.text((_PADDING, y), price_text, font=price_font, fill=_PRICE_COLOR)
        y += price_font.size + 8

        draw.text((_PADDING, y), _truncate(ad_caption, 70), font=body_font, fill=_TEXT_COLOR)

        if shg_name:
            watermark = _truncate(shg_name, 30)
            wm_bbox = draw.textbbox((0, 0), watermark, font=body_font)
            wm_w = wm_bbox[2] - wm_bbox[0]
            draw.text((w - wm_w - _PADDING, banner_h - body_font.size - 12), watermark, font=body_font, fill=_TEXT_COLOR)

        poster.paste(banner.convert("RGB"), (0, h))

        out = io.BytesIO()
        poster.save(out, format="JPEG", quality=90, optimize=True)
        return out.getvalue()
    except Exception:
        logger.exception("poster composite failed, falling back to plain image")
        return None


async def generate_poster(
    processed_image_bytes: bytes,
    *,
    product_name: str,
    ad_caption: str,
    price_min: float,
    price_max: float,
    shg_name: str = "",
) -> tuple[bytes | None, str]:
    """Two-tier poster generation, called by catalog_node.py:

      1. Flux Pro (optional, paid) — richer AI-generated poster. Only
         attempted if FLUX_API_KEY is set. See flux_poster_client.py for
         the open verification item on its request/response shape.
      2. Local Pillow composite (compose_poster, above) — free, always
         available, the permanent fallback regardless of Flux's status or
         configuration.

    Returns (image_bytes | None, tier_used). tier_used is "flux-pro" or
    "pillow" so catalog_node can log/trace which tier actually produced the
    delivered poster. None means both tiers failed (e.g. missing Bengali
    font AND Flux unavailable/unconfigured) — caller falls back further to
    plain photo + separate caption messages, same as before this change.
    """
    s = get_settings()

    if s.flux_api_key:
        try:
            image_bytes = await generate_poster_image(
                reference_image_bytes=processed_image_bytes,
                product_name=product_name,
                ad_caption=ad_caption,
                price_min=price_min,
                price_max=price_max,
                shg_name=shg_name,
            )
            return image_bytes, "flux-pro"
        except FluxUnavailableError as exc:
            logger.warning("Flux Pro poster generation failed, falling back to Pillow: %s", exc)

    pillow_bytes = await asyncio.to_thread(
        compose_poster,
        processed_image_bytes,
        product_name=product_name,
        ad_caption=ad_caption,
        price_min=price_min,
        price_max=price_max,
        shg_name=shg_name,
    )
    return pillow_bytes, "pillow"


def _truncate(text: str, max_chars: int) -> str:
    text = text.strip().replace("\n", " ")
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"
