
from __future__ import annotations

import io

from PIL import Image
from rembg import remove, new_session

_session = None

_BG_TOP = (250, 245, 235)
_BG_BOTTOM = (232, 220, 198)

MIN_RESOLUTION_PX = 300

def _get_session():
    global _session
    if _session is None:
        _session = new_session("u2net")
    return _session

def _quality_check(img: Image.Image) -> str | None:

    if min(img.size) < MIN_RESOLUTION_PX:
        return "ছবিটা একটু ছোট বা অস্পষ্ট। আরো কাছ থেকে, ভালো আলোয় তুলুন।"
    return None

def _gradient_background(size: tuple[int, int]) -> Image.Image:
    w, h = size
    bg = Image.new("RGB", size)
    pixels = bg.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(_BG_TOP[0] + (_BG_BOTTOM[0] - _BG_TOP[0]) * t)
        g = int(_BG_TOP[1] + (_BG_BOTTOM[1] - _BG_TOP[1]) * t)
        b = int(_BG_TOP[2] + (_BG_BOTTOM[2] - _BG_TOP[2]) * t)
        for x in range(w):
            pixels[x, y] = (r, g, b)
    return bg

def process_product_image(raw_bytes: bytes) -> tuple[bytes | None, str | None]:

    try:
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    except Exception:
        return None, "ছবিটা খুলতে পারলাম না। আবার পাঠান।"

    error = _quality_check(img)
    if error:
        return None, error

    cutout = remove(raw_bytes, session=_get_session())
    cutout_img = Image.open(io.BytesIO(cutout)).convert("RGBA")

    background = _gradient_background(cutout_img.size).convert("RGBA")
    composite = Image.alpha_composite(background, cutout_img).convert("RGB")

    out = io.BytesIO()
    composite.save(out, format="PNG", optimize=True)
    return out.getvalue(), None
