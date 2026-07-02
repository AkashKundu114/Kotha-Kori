
from __future__ import annotations

from sqlalchemy import select

from services.orchestrator.state import ConversationState
from shared.db.models import User
from shared.db.session import get_db_session

async def load_user_profile_node(state: ConversationState) -> dict:
    whatsapp_number = state["whatsapp_number"]

    async with get_db_session() as db:
        user = (
            await db.execute(select(User).where(User.whatsapp_number == whatsapp_number))
        ).scalar_one_or_none()

    if user is None:

        return {"is_new_user": True, "user_id": None, "user_profile": None, "trace": ["load_user_profile:new_user"]}

    profile = {
        "business_categories": user.business_categories or [],
        "self_reported_literacy": user.self_reported_literacy,
        "preferred_modality": user.preferred_modality,
        "dialect_hint": user.dialect_hint,
        "ledger_correction_rate": float(user.ledger_correction_rate or 0.0),
        "trust_stage": user.trust_stage,
        "block": user.block,
        "district": user.district,
    }
    return {
        "is_new_user": False,
        "user_id": str(user.id),
        "user_profile": profile,
        "trace": ["load_user_profile:loaded"],
    }
