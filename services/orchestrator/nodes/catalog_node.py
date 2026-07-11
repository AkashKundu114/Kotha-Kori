from __future__ import annotations

import asyncio
import logging
import uuid

from shared.config.settings import get_settings
from shared.storage.s3_client import get_s3_client
from services.orchestrator.state import ConversationState
from services.vision_service.rembg_processor import process_product_image
from services.vision_service.vision_router import analyze_product_image, generate_captions
from services.vision_service.poster_composer import compose_poster
from services.orchestrator.model_router import ModelUnavailableError
from services.market_service.aggregator import block_sales_trend, classify_trend

logger = logging.getLogger("catalog_node")

MAX_IMAGE_BYTES = 5 * 1024 * 1024

# Best-effort keyword bridge between the vision model's coarse category
# (textile/food/handicraft/agriculture/other) and the freeform Bengali
# category strings ledger entries use. Deliberately conservative — if
# nothing matches, we say nothing rather than fabricate a market claim.
_CATEGORY_KEYWORDS = {
    "textile": ["কাঁথা", "শাড়ি", "সেলাই", "কাপড়"],
    "food": ["পাপড়", "আচার", "মশলা", "খাবার"],
    "handicraft": ["হস্তশিল্প", "কারুকাজ"],
    "agriculture": ["সবজি", "ফসল", "চাষ"],
}


async def catalog_node(state: ConversationState) -> dict:
    s = get_settings()
    raw_key = state.get("raw_image_s3_key")
    if not raw_key:
        return {
            "outbound_messages": [{"type": "text", "body": "ছবিটা পেলাম না। আবার পাঠান।"}],
            "trace": ["catalog_node:no_image_key"],
        }

    s3 = get_s3_client()
    try:
        obj = await asyncio.to_thread(s3.get_object, Bucket=s.s3_bucket, Key=raw_key)
        raw_bytes = obj["Body"].read()
    except Exception:
        return {
            "outbound_messages": [{"type": "text", "body": "ছবিটা লোড করতে সমস্যা হয়েছে। আবার পাঠান।"}],
            "trace": ["catalog_node:s3_fetch_failed"],
        }

    if len(raw_bytes) > MAX_IMAGE_BYTES:
        return {
            "outbound_messages": [{"type": "text", "body": "ছবিটা অনেক বড়। একটু ছোট সাইজে পাঠান।"}],
            "trace": ["catalog_node:oversized_image"],
        }

    processed_bytes, quality_error = await asyncio.to_thread(process_product_image, raw_bytes)
    if quality_error:
        return {
            "outbound_messages": [{"type": "text", "body": quality_error}],
            "trace": ["catalog_node:quality_check_failed"],
        }

    try:
        # Vision understanding stays OpenAI-only (Sarvam has no comparable
        # capability); caption generation is routed through the cheap Sarvam
        # tier automatically via route_completion inside generate_captions.
        product_info = await analyze_product_image(raw_bytes)
        captions, (price_min, price_max) = await generate_captions(product_info, shg_name=_shg_name(state))
    except ModelUnavailableError:
        return {
            "outbound_messages": [{"type": "text", "body": "এই মুহূর্তে ছবি প্রসেস করতে সমস্যা হচ্ছে। একটু পরে আবার পাঠান।"}],
            "trace": ["catalog_node:model_unavailable"],
        }

    market_note = await _market_note(state, product_info.get("category", "other"))

    processed_key = f"catalog/{state.get('user_id', 'unknown')}/{uuid.uuid4().hex[:10]}.png"
    try:
        await asyncio.to_thread(
            s3.put_object, Bucket=s.s3_bucket, Key=processed_key, Body=processed_bytes,
            ContentType="image/png", ServerSideEncryption="AES256",
        )
    except Exception:
        return {
            "outbound_messages": [{"type": "text", "body": "ছবি সংরক্ষণ করতে সমস্যা হয়েছে। আবার চেষ্টা করুন।"}],
            "trace": ["catalog_node:s3_upload_failed"],
        }

    outbound_messages, poster_key = await _build_delivery_messages(
        s3, s, processed_bytes, processed_key, product_info, captions, price_min, price_max,
        market_note, state,
    )

    await _record_creation(state, raw_key, poster_key or processed_key, product_info, captions, price_min, price_max)

    return {
        "catalog_result": {
            "product_type": product_info.get("product_type"),
            "caption_bengali": captions["whatsapp_caption"],
            "ad_caption_bengali": captions["ad_caption"],
            "price_min": price_min,
            "price_max": price_max,
            "processed_s3_key": poster_key or processed_key,
        },
        "outbound_messages": outbound_messages,
        "trace": [f"catalog_node:done:{product_info.get('vision_model_used')}:poster={bool(poster_key)}"],
    }


async def _build_delivery_messages(s3, s, processed_bytes, processed_key, product_info, captions, price_min, price_max, market_note, state):
    """Tries to composite a single shareable poster (photo + price + caption
    banner). Falls back to the original photo + separate caption messages if
    the Bengali font asset isn't installed — see assets/fonts/README.md."""
    ad_caption_full = captions["ad_caption"] + (f"\n{market_note}" if market_note else "")

    poster_bytes = await asyncio.to_thread(
        compose_poster,
        processed_bytes,
        product_name=product_info.get("product_type", "পণ্য"),
        ad_caption=ad_caption_full,
        price_min=price_min,
        price_max=price_max,
        shg_name=_shg_name(state),
    )

    if poster_bytes:
        poster_key = processed_key.replace(".png", "-poster.jpg")
        try:
            await asyncio.to_thread(
                s3.put_object, Bucket=s.s3_bucket, Key=poster_key, Body=poster_bytes,
                ContentType="image/jpeg", ServerSideEncryption="AES256",
            )
            poster_url = s3.generate_presigned_url(
                "get_object", Params={"Bucket": s.s3_bucket, "Key": poster_key}, ExpiresIn=86400
            )
            return (
                [
                    {"type": "image", "url": poster_url, "caption": captions["whatsapp_caption"]},
                    {"type": "text", "body": "ইংরেজিতেও ক্যাপশন চান? (শহুরে কাস্টমারদের জন্য) — 'হ্যাঁ' লিখুন।"},
                ],
                poster_key,
            )
        except Exception:
            logger.warning("poster upload failed, falling back to plain image delivery")

    processed_url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": s.s3_bucket, "Key": processed_key}, ExpiresIn=86400
    )
    messages = [
        {"type": "image", "url": processed_url, "caption": captions["whatsapp_caption"]},
        {"type": "text", "body": "📣 বিজ্ঞাপনের জন্য এই সংক্ষিপ্ত বার্তাটিও ব্যবহার করতে পারেন:\n\n" + ad_caption_full},
        {"type": "text", "body": "ইংরেজিতেও ক্যাপশন চান? (শহুরে কাস্টমারদের জন্য) — 'হ্যাঁ' লিখুন।"},
    ]
    return messages, None


async def _market_note(state: ConversationState, vision_category: str) -> str | None:
    """Best-effort, privacy-respecting market signal (reuses Feature 8's
    k-anonymized aggregator, so the same 5-distinct-seller floor applies).
    Returns None — never a fabricated claim — if nothing matches."""
    profile = state.get("user_profile") or {}
    block = profile.get("block")
    keywords = _CATEGORY_KEYWORDS.get(vision_category)
    if not block or not keywords:
        return None

    try:
        rows = await block_sales_trend(block)
    except Exception:
        return None  # optional enrichment — never block catalog delivery on this

    by_category: dict[str, list[dict]] = {}
    for row in rows:
        cat = row["category"] or ""
        if any(kw in cat for kw in keywords):
            by_category.setdefault(cat, []).append(row)

    for series in by_category.values():
        series_sorted = sorted(series, key=lambda r: r["week"] or "", reverse=True)
        if classify_trend(series_sorted) == "rising":
            return "📈 আপনার এলাকায় এই ধরনের পণ্যের চাহিদা বাড়ছে — এখনই ভালো সময় বিক্রির জন্য!"
    return None


def _shg_name(state: ConversationState) -> str:
    profile = state.get("user_profile") or {}
    return profile.get("shg_name", "")


async def _record_creation(state, raw_key, processed_key, product_info, captions, price_min, price_max) -> None:
    user_id = state.get("user_id")
    if not user_id:
        return
    try:
        from shared.db.session import get_db_session
        from shared.db.models import CatalogCreation

        async with get_db_session() as db:
            db.add(
                CatalogCreation(
                    user_id=user_id,
                    raw_image_s3_key=raw_key,
                    processed_image_s3_key=processed_key,
                    product_type=product_info.get("product_type"),
                    caption_bengali=captions["whatsapp_caption"],
                    ad_caption_bengali=captions["ad_caption"],
                    price_suggestion_min=price_min,
                    price_suggestion_max=price_max,
                    vision_model_used=product_info.get("vision_model_used"),
                )
            )
            await db.commit()
    except Exception:
        pass  # the WhatsApp reply already went out; a failed audit-row write shouldn't retry the whole turn
