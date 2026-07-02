from __future__ import annotations

import json
import re

from services.orchestrator.model_router import (
    route_vision_completion,
    route_completion,
    TaskCriticality,
)

VISION_PROMPT = (
    "এই ছবিতে কী পণ্য দেখছ? শুধুমাত্র এই JSON ফরম্যাটে ফেরত দাও:\n"
    "{\"product_type\": \"<ইংরেজিতে সংক্ষিপ্ত, যেমন 'kantha saree'>\",\n"
    " \"material\": \"<যদি বোঝা যায়>\",\n"
    " \"notable_features\": [\"<২-৩টি লক্ষণীয় বৈশিষ্ট্য>\"],\n"
    " \"category\": \"<textile|food|handicraft|agriculture|other>\"}"
)

CAPTION_SYSTEM = (
    "তুমি গ্রামীণ স্বনির্ভর গোষ্ঠীর মহিলাদের জন্য একজন বিজ্ঞাপন লেখক।\n"
    "দেওয়া পণ্যের তথ্যের ভিত্তিতে সহজ, আকর্ষণীয় বাংলায় একটি ছোট বিক্রির বার্তা লেখো।\n"
    "নিয়ম:\n"
    "1. ৪ লাইনের বেশি নয়।\n"
    "2. পণ্যের নাম, ১-২টি বৈশিষ্ট্য, একটি দামের পরিসীমা (₹X-₹Y অনুমান করে, বাস্তবসম্মত), একটি সংক্ষিপ্ত CTA।\n"
    "3. অতিরিক্ত প্রতিশ্রুতি বা মিথ্যা দাবি করো না — শুধু যা ছবিতে দেখা যাচ্ছে তার ভিত্তিতে লেখো।\n"
    "4. শুধু বার্তাটি ফেরত দাও, অন্য কোনো ব্যাখ্যা নয়।"
)

_PRICE_RANGES = {
    "textile": (500, 1500),
    "food": (50, 400),
    "handicraft": (150, 800),
    "agriculture": (30, 300),
    "other": (100, 600),
}

async def analyze_product_image(image_bytes: bytes) -> dict:

    result = await route_vision_completion(
        prompt=VISION_PROMPT, image_bytes=image_bytes, criticality=TaskCriticality.ROUTINE
    )
    try:
        parsed = json.loads(re.sub(r"```json|```", "", result["text"]).strip())
    except (json.JSONDecodeError, TypeError):
        parsed = {"product_type": "পণ্য", "category": "other", "notable_features": []}

    parsed["vision_model_used"] = result["model_used"]
    parsed.setdefault("category", "other")
    return parsed

async def generate_caption(product_info: dict, shg_name: str = "") -> tuple[str, tuple[float, float]]:

    category = product_info.get("category", "other")
    price_min, price_max = _PRICE_RANGES.get(category, _PRICE_RANGES["other"])

    prompt = (
        f"পণ্যের তথ্য: {json.dumps(product_info, ensure_ascii=False)}\n"
        f"দামের পরিসীমা নির্দেশিকা: ₹{price_min}-₹{price_max}\n"
        f"গোষ্ঠীর নাম (যদি থাকে): {shg_name}\n\n"
        "উপরের তথ্যের ভিত্তিতে বিক্রির বার্তা লেখো।"
    )
    result = await route_completion(
        system=CAPTION_SYSTEM, prompt=prompt, criticality=TaskCriticality.ROUTINE, confidence_floor=0.0
    )

    return result["text"].strip(), (price_min, price_max)
