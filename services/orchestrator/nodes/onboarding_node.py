
from __future__ import annotations

from services.orchestrator.state import ConversationState

WELCOME = (
    "🙏 কোথা-খাতায় আপনাকে স্বাগতম!\n\n"
    "আমি আপনার ব্যবসার হিসাব রাখব, পণ্যের বিজ্ঞাপন বানাব, "
    "আর বাজারের পরামর্শ দেব।\n\n"
    "শুরু করতে আপনার নাম বলুন।"
)

async def onboarding_node(state: ConversationState) -> dict:
    step = state.get("onboarding_step", "WELCOME")
    text = (state.get("raw_input_text") or state.get("raw_input_transcript") or "").strip()

    if step == "WELCOME":

        return {
            "onboarding_step": "AWAIT_NAME",
            "outbound_messages": [{"type": "text", "body": WELCOME}],
            "trace": ["onboarding_node:welcome"],
        }

    if step == "AWAIT_NAME":
        return {
            "onboarding_name": text,
            "onboarding_step": "AWAIT_BLOCK",
            "outbound_messages": [{"type": "text", "body": f"{text} দি, আপনি কোন ব্লকে থাকেন?"}],
            "trace": ["onboarding_node:got_name"],
        }

    if step == "AWAIT_BLOCK":
        return {
            "onboarding_block": text,
            "onboarding_step": "AWAIT_CONSENT",
            "outbound_messages": [
                {
                    "type": "text",
                    "body": (
                        "কোথা-খাতা ব্যবহারের আগে:\n"
                        "✅ আপনার হিসাব শুধু আপনি দেখতে পাবেন\n"
                        "✅ কোনো ব্যক্তিগত তথ্য বিক্রি হবে না\n"
                        "✅ ভয়েস মেসেজ প্রসেসিংয়ের পরপরই মুছে ফেলা হয়\n\n"
                        "রাজি থাকলে 'হ্যাঁ' লিখুন।"
                    ),
                }
            ],
            "trace": ["onboarding_node:got_block"],
        }

    if step == "AWAIT_CONSENT":
        if text.lower() not in {"হ্যাঁ", "হ্যা", "ha", "haan", "yes"}:
            return {
                "outbound_messages": [{"type": "text", "body": "রাজি হলে 'হ্যাঁ' লিখুন, তাহলে শুরু করতে পারব।"}],
                "trace": ["onboarding_node:consent_not_given"],
            }
        user_id = await _create_user(state)
        return {
            "user_id": user_id,
            "is_new_user": False,
            "onboarding_step": "DONE",
            "outbound_messages": [
                {
                    "type": "text",
                    "body": "✨ আপনার কোথা-খাতা তৈরি! আজকের বিক্রি বা খরচ ভয়েসে বলুন। 🎙️",
                }
            ],
            "trace": ["onboarding_node:complete"],
        }

    return {"outbound_messages": [{"type": "text", "body": "শুরু করতে 'শুরু' লিখুন।"}], "trace": ["onboarding_node:already_done"]}

async def _create_user(state: ConversationState) -> str:
    from datetime import datetime, timezone
    from shared.db.session import get_db_session
    from shared.db.models import User

    async with get_db_session() as db:
        user = User(
            whatsapp_number=state["whatsapp_number"],
            name=state.get("onboarding_name"),
            block=state.get("onboarding_block"),
            consent_given=True,
            consent_given_at=datetime.now(timezone.utc),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return str(user.id)
