from __future__ import annotations

from typing import Literal, TypedDict, Annotated
from operator import add

Feature = Literal["LEDGER", "LEDGER_REPORT", "CATALOG", "MARKET", "PRICING", "ONBOARDING", "IDLE"]


class PendingLedgerEntry(TypedDict, total=False):
    transactions: list[dict]
    overall_confidence: float
    raw_transcript: str
    extracted_by: str


class UserProfile(TypedDict, total=False):
    business_categories: list[str]
    self_reported_literacy: str
    preferred_modality: str
    dialect_hint: str
    ledger_correction_rate: float
    trust_stage: str
    block: str
    district: str


class ConversationState(TypedDict, total=False):
    whatsapp_number: str
    user_id: str | None
    is_new_user: bool
    user_profile: UserProfile | None

    onboarding_step: str | None
    onboarding_name: str | None
    onboarding_block: str | None

    active_feature: Feature
    last_message_type: Literal["text", "audio", "image", "interactive"]
    raw_input_text: str | None
    raw_input_transcript: str | None
    transcript_provider: str | None
    transcript_confidence: float | None

    pending_ledger_entry: PendingLedgerEntry | None
    awaiting_confirmation: bool
    ledger_confirmation_turns: int

    raw_image_s3_key: str | None
    catalog_result: dict | None

    market_query: str | None
    market_report: dict | None

    trace: Annotated[list[str], add]
    outbound_messages: Annotated[list[dict], add]
