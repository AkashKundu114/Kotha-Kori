from __future__ import annotations

from datetime import date

from services.orchestrator.state import ConversationState
from shared.i18n.bengali_calendar import GREGORIAN_MONTHS_BENGALI, format_bangla_calendar_label

# NOTE: this used to be a locally duplicated dict, identical to the one in
# pdf_service/generator.py. Both now import from
# shared/i18n/bengali_calendar.py — kept as a local alias so nothing else
# importing BENGALI_MONTHS from this module breaks.
BENGALI_MONTHS = GREGORIAN_MONTHS_BENGALI


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
            "outbound_messages": [{"type": "text", "body": f"{GREGORIAN_MONTHS_BENGALI[today.month]} মাসে কোনো হিসাব পাওয়া যায়নি।"}],
            "trace": ["ledger_report_node:no_entries"],
        }

    bangla_calendar_label = format_bangla_calendar_label(today)
    caption = (
        f"📄 {GREGORIAN_MONTHS_BENGALI[today.month]} {today.year} মাসের হিসাব "
        f"(বাংলা: {bangla_calendar_label}):\n\n"
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
