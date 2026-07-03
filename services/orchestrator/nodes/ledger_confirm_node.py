from __future__ import annotations

from datetime import datetime, timezone

from services.orchestrator.state import ConversationState
from services.orchestrator.model_router import route_completion, TaskCriticality

AFFIRMATIVE = {"হ্যাঁ", "হ্যা", "ha", "haan", "thik", "ঠিক", "ok", "okay", "👍"}
NEGATIVE = {"না", "no", "na", "bhul", "ভুল", "ঠিক নয়"}

MAX_CONFIRMATION_TURNS = 3


MAX_REASONABLE_AMOUNT = 500_000

CORRECTION_SYSTEM = (
    "তুমি বাংলা আর্থিক তথ্য নিষ্কাশনকারী। ব্যবহারকারী একটি পূর্বের\n"
    "নিষ্কাশনে সংশোধন দিয়েছেন। মূল বাক্য, পূর্বের ফলাফল এবং সংশোধনের ভিত্তিতে\n"
    "আপডেট করা JSON ফেরত দাও, একই ফরম্যাটে:\n\n"
    '{"transactions": [{"type": "INCOME"|"EXPENSE", "amount_inr": <number>,\n'
    ' "item_bengali": "...", "quantity": <number|null>, "unit": "...|null"}],\n'
    ' "confidence": <0.0-1.0>}'
)


def _validate_amount(amt: float) -> float | None:
    """Reject NaN/inf and out-of-range amounts before they ever reach the DB.
    See RED_TEAM_AUDIT_AND_FIXES.md HIGH-4."""
    if amt != amt or amt in (float("inf"), float("-inf")):
        return None
    if amt < 0 or amt > MAX_REASONABLE_AMOUNT:
        return None
    return round(amt, 2)


async def ledger_confirm_node(state: ConversationState) -> dict:
    reply_raw = (
        (state.get("raw_input_text") or state.get("raw_input_transcript") or "")
        .strip()
        .lower()
    )
    pending = state.get("pending_ledger_entry")
    turns = state.get("ledger_confirmation_turns", 0) + 1

    if not pending:
        return _reset_with_message(
            "একটু সমস্যা হয়েছে। আবার হিসাব বলুন।", trace="ledger_confirm_node:no_pending"
        )

    if turns > MAX_CONFIRMATION_TURNS:
        return _reset_with_message(
            "হিসাবটা বাদ দেওয়া হলো। নতুন করে বলুন কি বিক্রি বা খরচ হয়েছে।",
            trace="ledger_confirm_node:max_turns_exceeded",
        )

    if reply_raw in AFFIRMATIVE:
        return await _save(state, pending)

    if reply_raw in NEGATIVE or _looks_like_correction(reply_raw):
        return await _apply_correction(state, pending, reply_raw, turns)

    return {
        "awaiting_confirmation": True,
        "ledger_confirmation_turns": turns,
        "outbound_messages": [{"type": "text", "body": "বুঝলাম না। 'হ্যাঁ' বা 'না' বলুন।"}],
        "trace": [f"ledger_confirm_node:unrecognized_reply:turn={turns}"],
    }


def _looks_like_correction(text: str) -> bool:
    return any(ch.isdigit() for ch in text) or any("০" <= ch <= "৯" for ch in text)


async def _apply_correction(
    state: ConversationState, pending: dict, correction_text: str, turns: int
) -> dict:
    prompt = (
        f"মূল বাক্য: {pending.get('raw_transcript', '')}\n"
        f"পূর্বের ফলাফল: {pending}\n"
        f"ব্যবহারকারীর সংশোধন: {correction_text}\n\n"
        "সংশোধন প্রয়োগ করে আপডেট করা JSON ফেরত দাও।"
    )
    result = await route_completion(
        system=CORRECTION_SYSTEM,
        prompt=prompt,
        criticality=TaskCriticality.ROUTINE,
        confidence_floor=0.80,
    )

    import json
    import re

    try:
        parsed = json.loads(re.sub(r"```json|```", "", result["text"]).strip())
    except json.JSONDecodeError:
        return {
            "awaiting_confirmation": True,
            "ledger_confirmation_turns": turns,
            "outbound_messages": [
                {"type": "text", "body": "সংশোধন বুঝতে পারলাম না। আবার বলুন?"}
            ],
            "trace": [f"ledger_confirm_node:correction_parse_failed:turn={turns}"],
        }

    updated = {
        "transactions": parsed.get("transactions", pending.get("transactions", [])),
        "overall_confidence": parsed.get("confidence", 0.0),
        "raw_transcript": pending.get("raw_transcript", ""),
        "extracted_by": result["model_used"],
    }

    from services.orchestrator.nodes.ledger_node import _build_confirmation

    return {
        "pending_ledger_entry": updated,
        "awaiting_confirmation": True,
        "ledger_confirmation_turns": turns,
        "outbound_messages": [
            {
                "type": "text",
                "body": f"ঠিক আছে, আবার দেখুন:\n\n{_build_confirmation(updated)}",
            }
        ],
        "trace": [
            f"ledger_confirm_node:correction_applied:turn={turns}:{result['model_used']}"
        ],
    }


async def _save(state: ConversationState, pending: dict) -> dict:
    from shared.db.session import get_db_session
    from shared.db.models import LedgerEntry

    user_id = state.get("user_id")
    if not user_id:
        return _reset_with_message(
            "হিসাব রাখতে সমস্যা হয়েছে। একটু পরে আবার চেষ্টা করুন।",
            trace="ledger_confirm_node:save_failed_no_user_id",
        )

    validated: list[tuple[dict, float]] = []
    for tx in pending.get("transactions", []):
        raw_amt = float(tx.get("amount_inr", 0) or 0)
        amt = _validate_amount(raw_amt)
        if amt is None:
            return _reset_with_message(
                "টাকার পরিমাণটা ঠিক বুঝতে পারলাম না। আবার বলুন, যেমন: '৩০০ টাকা পাপড় বিক্রি করেছি'",
                trace="ledger_confirm_node:amount_out_of_range",
            )
        validated.append((tx, amt))

    total_income, total_expense = 0.0, 0.0
    saved_count = 0

    try:
        async with get_db_session() as db:
            for tx, amt in validated:
                entry = LedgerEntry(
                    user_id=user_id,
                    entry_type=tx.get("type", "INCOME"),
                    amount_inr=amt,
                    category=tx.get("item_bengali"),
                    description_bengali=tx.get("item_bengali"),
                    quantity=tx.get("quantity"),
                    unit=tx.get("unit"),
                    raw_transcript=pending.get("raw_transcript"),
                    is_corrected=pending.get("extracted_by") is not None
                    and state.get("ledger_confirmation_turns", 0) > 0,
                    extracted_by=pending.get("extracted_by"),
                )
                db.add(entry)
                saved_count += 1
                if tx.get("type") == "INCOME":
                    total_income += amt
                else:
                    total_expense += amt
            await db.commit()
    except Exception:
        return _reset_with_message(
            "হিসাব রাখতে সমস্যা হয়েছে। একটু পরে আবার চেষ্টা করুন।",
            trace="ledger_confirm_node:db_commit_failed",
        )

    success_msg = (
        f"✅ হিসাব রাখা হয়েছে!\n\n"
        f"এই বার্তায়:\n📈 আয়: ₹{total_income:.0f}\n📉 খরচ: ₹{total_expense:.0f}\n"
        f"💰 লাভ: ₹{total_income - total_expense:.0f}\n\n"
        f"মাসের শেষে রিপোর্ট পেতে 'রিপোর্ট' লিখুন।"
    )
    return {
        "pending_ledger_entry": None,
        "awaiting_confirmation": False,
        "ledger_confirmation_turns": 0,
        "outbound_messages": [{"type": "text", "body": success_msg}],
        "trace": [f"ledger_confirm_node:saved:{saved_count}_entries"],
    }


def _reset_with_message(msg: str, trace: str) -> dict:
    return {
        "pending_ledger_entry": None,
        "awaiting_confirmation": False,
        "ledger_confirmation_turns": 0,
        "outbound_messages": [{"type": "text", "body": msg}],
        "trace": [trace],
    }
