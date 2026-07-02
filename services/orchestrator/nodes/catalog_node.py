
from __future__ import annotations

import asyncio
import uuid

import boto3

from shared.config.settings import get_settings
from services.orchestrator.state import ConversationState
from services.vision_service.rembg_processor import process_product_image
from services.vision_service.vision_router import analyze_product_image, generate_caption

MAX_IMAGE_BYTES = 5 * 1024 * 1024

async def catalog_node(state: ConversationState) -> dict:
    s = get_settings()
    raw_key = state.get("raw_image_s3_key")
    if not raw_key:
        return {
            "outbound_messages": [{"type": "text", "body": "ছবিটা পেলাম না। আবার পাঠান।"}],
            "trace": ["catalog_node:no_image_key"],
        }

    s3 = boto3.client("s3", region_name=s.aws_region)
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

    product_info = await analyze_product_image(raw_bytes)
    caption, (price_min, price_max) = await generate_caption(product_info, shg_name=_shg_name(state))

    processed_key = f"catalog/{state.get('user_id', 'unknown')}/{uuid.uuid4().hex[:10]}.png"
    await asyncio.to_thread(
        s3.put_object,
        Bucket=s.s3_bucket,
        Key=processed_key,
        Body=processed_bytes,
        ContentType="image/png",
        ServerSideEncryption="AES256",
    )
    processed_url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": s.s3_bucket, "Key": processed_key}, ExpiresIn=86400
    )

    await _record_creation(state, raw_key, processed_key, product_info, caption, price_min, price_max)

    return {
        "catalog_result": {
            "product_type": product_info.get("product_type"),
            "caption_bengali": caption,
            "price_min": price_min,
            "price_max": price_max,
            "processed_s3_key": processed_key,
        },
        "outbound_messages": [
            {"type": "image", "url": processed_url, "caption": caption},
            {"type": "text", "body": "ইংরেজিতেও ক্যাপশন চান? (শহুরে কাস্টমারদের জন্য) — 'হ্যাঁ' লিখুন।"},
        ],
        "trace": [f"catalog_node:done:{product_info.get('vision_model_used')}"],
    }

def _shg_name(state: ConversationState) -> str:
    profile = state.get("user_profile") or {}
    return profile.get("shg_name", "")

async def _record_creation(state, raw_key, processed_key, product_info, caption, price_min, price_max) -> None:

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
                    caption_bengali=caption,
                    price_suggestion_min=price_min,
                    price_suggestion_max=price_max,
                    vision_model_used=product_info.get("vision_model_used"),
                )
            )
            await db.commit()
    except Exception:
        pass
