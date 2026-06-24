"""
Master intent router — dispatches incoming messages to correct Celery task.
"""
from shared.whatsapp.parser import IncomingMessage
from shared.redis.session_manager import get_session, set_session
from services.ai_worker import tasks

FINANCIAL_KEYWORDS = {"bikri","বিক্রি","kharach","খরচ","hisab","হিসাব","taka","টাকা","labh","লাভ"}
SCHEME_KEYWORDS    = {"prakalpa","প্রকল্প","yojana","যোজনা","lakshmir","লক্ষ্মীর","svskp","jaago","anandadhara"}
MEETING_KEYWORDS   = {"sobha","সভা","mishon","মিটিং","boisak","বৈঠক","hajira","হাজিরা"}
REPORT_KEYWORDS    = {"report","রিপোর্ট","maaser","মাসের","hisab"}
TRAINING_KEYWORDS  = {"shikhte","শিখতে","training","course","কোর্স"}
AGRI_KEYWORDS      = {"chasha","চাষ","khet","ক্ষেত","gach","গাছ","rog","রোগ","murgi","মুরগি"}

async def route_message(msg: IncomingMessage):
    session = await get_session(msg.from_number)
    state   = session.get("state", "IDLE")

    # ── Resume active flow ─────────────────────────────────────────
    if state != "IDLE":
        tasks.resume_flow.delay(msg.from_number, msg.__dict__, session)
        return

    # ── New user → onboarding ──────────────────────────────────────
    from shared.db.session import get_db
    # (Check if user exists in DB; if not → onboarding)
    # ... abbreviated for skeleton

    # ── Image routing ──────────────────────────────────────────────
    if msg.message_type == "image":
        caption = (msg.caption or "").lower()
        if any(k in caption for k in AGRI_KEYWORDS):
            tasks.process_agri_image.delay(msg.from_number, msg.image_id)
        else:
            tasks.process_catalog_image.delay(msg.from_number, msg.image_id)
        return

    # ── Keyword-based routing ──────────────────────────────────────
    text = ""
    if msg.message_type == "text":
        text = msg.text.lower()
    elif msg.message_type == "audio":
        # Quick keyword routing will happen after STT in the worker
        tasks.process_voice_route.delay(msg.from_number, msg.audio_id)
        return

    if any(k in text for k in FINANCIAL_KEYWORDS):
        tasks.process_text_ledger.delay(msg.from_number, msg.text)
    elif any(k in text for k in SCHEME_KEYWORDS):
        tasks.process_scheme_query.delay(msg.from_number, msg.text)
    elif any(k in text for k in MEETING_KEYWORDS):
        tasks.process_meeting_start.delay(msg.from_number)
    elif any(k in text for k in REPORT_KEYWORDS):
        tasks.generate_ledger_report.delay(msg.from_number, msg.text)
    elif any(k in text for k in TRAINING_KEYWORDS):
        tasks.process_training_request.delay(msg.from_number, msg.text)
    elif msg.text in ("HELP", "help", "সাহায্য", "menu", "MENU"):
        tasks.send_help_menu.delay(msg.from_number)
    else:
        tasks.classify_intent_llm.delay(msg.from_number, msg.text or "")
