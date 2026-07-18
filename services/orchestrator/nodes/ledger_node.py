from __future__ import annotations

import json
import logging
import re

from services.orchestrator.state import ConversationState
from services.orchestrator.model_router import (
    route_completion,
    route_translation,
    TaskCriticality,
    ModelUnavailableError,
)

logger = logging.getLogger("ledger_node")

_LATIN_LETTER_RE = re.compile(r"[A-Za-z]")
_BENGALI_LETTER_RE = re.compile(r"[\u0980-\u09FF]")
_BANGLISH_LATIN_RATIO_THRESHOLD = 0.35


def _looks_code_mixed(text: str) -> bool:
    latin = len(_LATIN_LETTER_RE.findall(text))
    bengali = len(_BENGALI_LETTER_RE.findall(text))
    total_letters = latin + bengali
    if total_letters < 6:
        return False
    return (latin / total_letters) >= _BANGLISH_LATIN_RATIO_THRESHOLD


async def _normalize_transcript(transcript: str) -> str:
    if not _looks_code_mixed(transcript):
        return transcript
    try:
        result = await route_translation(transcript, target_lang="bn-IN")
        return result["text"] or transcript
    except ModelUnavailableError:
        logger.warning("translation normalization failed, extracting from raw transcript instead")
        return transcript

EXTRACTION_SYSTEM = (
    "তুমি বাংলা আর্থিক তথ্য নিষ্কাশনকারী। নিচের বাংলা টেক্সট থেকে\n"
    "লেনদেন বের করো এবং শুধুমাত্র এই JSON ফরম্যাটে ফেরত দাও, অন্য কিছু লিখো না:\n\n"
    '{"transactions": [{"type": "INCOME"|"EXPENSE", "amount_inr": <number>,\n'
    ' "item_bengali": "...", "quantity": <number|null>, "unit": "...|null"}],\n'
    ' "confidence": <0.0-1.0>}\n\n'
    "Bengali number words: এক=1, দুই=2, তিন=3, চার=4, পাঁচ=5, দশ=10, পনেরো=15,\n"
    "বিশ=20, পঁচিশ=25, ত্রিশ=30, পঞ্চাশ=50, একশো=100, দুইশো=200, তিনশো=300,\n"
    "পাঁচশো=500, হাজার=1000. Extract ALL transactions present, even if multiple."
)

BASE_CONFIDENCE_FLOOR = 0.80
MAX_FLOOR_ADJUSTMENT = 0.12
MODEL_DOWN_MESSAGE = (
    "এই মুহূর্তে হিসাব প্রসেস করতে সমস্যা হচ্ছে। একটু পরে আবার চেষ্টা করুন।"
)


def _personalized_confidence_floor(user_profile: dict | None) -> float:
    if not user_profile:
        return BASE_CONFIDENCE_FLOOR
    correction_rate = float(user_profile.get("ledger_correction_rate", 0.0) or 0.0)
    adjustment = min(MAX_FLOOR_ADJUSTMENT, correction_rate * MAX_FLOOR_ADJUSTMENT * 2)
    return min(0.95, BASE_CONFIDENCE_FLOOR + adjustment)


def _strip_json_fences(text: str) -> str:
    return re.sub(r"```json|```", "", text).strip()


async def ledger_extract_node(state: ConversationState) -> dict:
    original_transcript = state.get("raw_input_transcript") or state.get("raw_input_text") or ""
    transcript = await _normalize_transcript(original_transcript)
    confidence_floor = _personalized_confidence_floor(state.get("user_profile"))

    try:
        result = await route_completion(
            system=EXTRACTION_SYSTEM,
            prompt=transcript,
            criticality=TaskCriticality.ROUTINE,
            confidence_floor=confidence_floor,
        )
    except ModelUnavailableError:
        return {
            "pending_ledger_entry": None,
            "awaiting_confirmation": False,
            "outbound_messages": [{"type": "text", "body": MODEL_DOWN_MESSAGE}],
            "trace": ["ledger_extract_node:model_unavailable"],
        }

    try:
        parsed = json.loads(_strip_json_fences(result["text"]))
    except json.JSONDecodeError:
        parsed = {"transactions": [], "confidence": 0.0}

    pending = {
        "transactions": parsed.get("transactions", []),
        "overall_confidence": parsed.get("confidence", 0.0),
        "raw_transcript": transcript,
        "extracted_by": result["model_used"],
    }

    if pending["overall_confidence"] < 0.5 or not pending["transactions"]:
        clarify_msg = (
            "একটু পরিষ্কার হলো না। আবার বলুন? "
            "যেমন: '৩০০ টাকা পাপড় বিক্রি করেছি, ১০০ টাকা মশলা কিনেছি'"
        )
        return {
            "pending_ledger_entry": None,
            "awaiting_confirmation": False,
            "outbound_messages": [{"type": "text", "body": clarify_msg}],
            "trace": [f"ledger_extract_node:clarify:{result['model_used']}"],
        }

    confirmation = _build_confirmation(pending)
    return {
        "pending_ledger_entry": pending,
        "awaiting_confirmation": True,
        "ledger_confirmation_turns": 0,
        "outbound_messages": [{"type": "text", "body": confirmation}],
        "trace": [f"ledger_extract_node:confirm:{result['model_used']}:floor={confidence_floor:.2f}"],
    }


def _build_confirmation(pending: dict) -> str:
    lines = ["আমি এইটুকু বুঝলাম:"]
    total_income, total_expense = 0, 0
    for tx in pending["transactions"]:
        amt = tx.get("amount_inr", 0)
        if tx.get("type") == "INCOME":
            total_income += amt
            lines.append(f"✅ আয়: {tx.get('item_bengali', '')} → ₹{amt}")
        else:
            total_expense += amt
            lines.append(f"📤 খরচ: {tx.get('item_bengali', '')} → ₹{amt}")
    lines.append(f"\n💰 লাভ: ₹{total_income - total_expense}")
    lines.append("\nঠিক আছে? (হ্যাঁ/না)")
    return "\n".join(lines)
