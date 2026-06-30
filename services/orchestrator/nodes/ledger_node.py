"""
Ledger extraction node — ROUTINE task, cascades local Qwen -> Claude on
low confidence. This is the highest-volume node in the system, so keeping it
off Claude by default is where most of the cost saving from the original
"zero-cost LLM" goal actually comes from in v2 — without sacrificing accuracy
on the calls that need it.
"""
from __future__ import annotations

import json
import re

from services.orchestrator.state import ConversationState
from services.orchestrator.model_router import route_completion, TaskCriticality

EXTRACTION_SYSTEM = """তুমি বাংলা আর্থিক তথ্য নিষ্কাশনকারী। নিচের বাংলা টেক্সট থেকে
লেনদেন বের করো এবং শুধুমাত্র এই JSON ফরম্যাটে ফেরত দাও, অন্য কিছু লিখো না:

{"transactions": [{"type": "INCOME"|"EXPENSE", "amount_inr": <number>,
 "item_bengali": "...", "quantity": <number|null>, "unit": "...|null"}],
 "confidence": <0.0-1.0>}"""


def _strip_json_fences(text: str) -> str:
    return re.sub(r"```json|```", "", text).strip()


async def ledger_extract_node(state: ConversationState) -> dict:
    transcript = state.get("raw_input_transcript") or state.get("raw_input_text") or ""

    result = await route_completion(
        system=EXTRACTION_SYSTEM,
        prompt=transcript,
        criticality=TaskCriticality.ROUTINE,
        confidence_floor=0.80,
    )

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
            "outbound_messages": [{"type": "text", "body": clarify_msg}],
            "trace": [f"ledger_extract_node:clarify:{result['model_used']}"],
        }

    confirmation = _build_confirmation(pending)
    return {
        "pending_ledger_entry": pending,
        "outbound_messages": [{"type": "text", "body": confirmation}],
        "trace": [f"ledger_extract_node:confirm:{result['model_used']}:escalated={result['escalated']}"],
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
