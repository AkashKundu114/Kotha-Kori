"""
Typed state for the Kotha-Khata conversation graph.

This replaces the old convention-based Redis hash
(`session:{number}` with loosely-typed `context` JSON blobs) with a single
typed object that LangGraph checkpoints automatically. Every node reads and
returns a partial update to this state — nothing is implicit.
"""
from __future__ import annotations

from typing import Literal, TypedDict, Annotated
from operator import add


Feature = Literal[
    "LEDGER", "SCHEME_RAG", "CATALOG", "AGRI", "MEETING", "TRAINING", "ONBOARDING", "IDLE"
]


class PendingLedgerEntry(TypedDict, total=False):
    transactions: list[dict]
    overall_confidence: float
    raw_transcript: str
    extracted_by: str  # "qwen-local" | "claude" — which model produced this


class ConversationState(TypedDict, total=False):
    # Identity
    whatsapp_number: str
    user_id: str | None
    is_new_user: bool

    # Routing
    active_feature: Feature
    last_message_type: Literal["text", "audio", "image", "interactive"]
    raw_input_text: str | None
    raw_input_transcript: str | None
    transcript_provider: str | None  # "sarvam" | "bhashini" | "whisper-local"
    transcript_confidence: float | None

    # Ledger sub-state
    pending_ledger_entry: PendingLedgerEntry | None

    # Scheme RAG sub-state
    scheme_query: str | None
    scheme_filter: list[str] | None
    retrieved_chunks: list[dict] | None
    draft_answer_bengali: str | None
    grounding_report: dict | None  # output of grounding_verifier
    final_answer_bengali: str | None

    # Bookkeeping — append-only audit trail of every node visited this turn.
    # Annotated with `add` so LangGraph merges across nodes instead of overwriting.
    trace: Annotated[list[str], add]

    # Output queue — messages this turn produced, sent at the end of graph execution
    outbound_messages: Annotated[list[dict], add]
