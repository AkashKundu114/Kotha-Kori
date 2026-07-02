
from __future__ import annotations

from datetime import date

from services.orchestrator.state import ConversationState

BENGALI_MONTHS = {
    1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল",
    5: "মে", 6: "জুন", 7: "জুলাই", 8: "আগস্ট",
    9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর",
}

async def ledger_report_node(state: ConversationState) -> dict:
    user_id = state.get("user_id")
    if not user_id:
        return {
            "outbound_messages": [{"type": "text", "body": "আগে হিসাব শুরু করুন, তারপর রিপোর্ট পাবেন।"}],
            "trace": ["ledger_report_node:no_user"],
        }

    today = date.today()

    from services.pdf_service.generator import generate_monthly_report

    try:
        result = await generate_monthly_report(user_id=user_id, year=today.year, month=today.month)
    except Exception as exc:
        return {
            "outbound_messages": [{"type": "text", "body": "রিপোর্ট তৈরি করতে সমস্যা হয়েছে। একটু পরে আবার চেষ্টা করুন।"}],
            "trace": [f"ledger_report_node:generation_failed:{type(exc).__name__}"],
        }

    if result["total_income"] == 0 and result["total_expense"] == 0:
        return {
            "outbound_messages": [
                {"type": "text", "body": f"{BENGALI_MONTHS[today.month]} মাসে কোনো হিসাব পাওয়া যায়নি।"}
            ],
            "trace": ["ledger_report_node:no_entries"],
        }

    caption = (
        f"📄 {BENGALI_MONTHS[today.month]} {today.year} মাসের হিসাব:\n\n"
        f"আয়: ₹{result['total_income']:.0f} | খরচ: ₹{result['total_expense']:.0f} | "
        f"লাভ: ₹{result['total_income'] - result['total_expense']:.0f}\n\n"
        f"এই PDF ব্যাংক বা পঞ্চায়েতে দেখাতে পারবেন।"
    )
    return {
        "outbound_messages": [
            {
                "type": "document",
                "url": result["s3_url"],
                "filename": f"kotha-khata-{today.year}-{today.month:02d}.pdf",
                "caption": caption,
            }
        ],
        "trace": ["ledger_report_node:sent"],
    }
