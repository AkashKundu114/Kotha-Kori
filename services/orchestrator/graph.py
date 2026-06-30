"""
The Kotha-Khata conversation graph.

Replaces: services/gateway/router.py (keyword dispatch) +
services/ai-worker/tasks.py (one Celery task per feature, each managing its
own slice of Redis state by convention).

Run via `graph.ainvoke(state, config={"configurable": {"thread_id": whatsapp_number}})`
from a Celery task (see services/orchestrator/celery_entrypoint.py) so the
20s WhatsApp webhook ack is never blocked by graph execution.
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from services.orchestrator.state import ConversationState
from services.orchestrator.nodes.intent_router import classify_intent
from services.orchestrator.nodes.ledger_node import ledger_extract_node
from services.orchestrator.nodes.scheme_rag_node import scheme_rag_node
from shared.config.settings import get_settings


def _route_after_intent(state: ConversationState) -> str:
    feature = state.get("active_feature", "IDLE")
    if feature == "LEDGER":
        return "ledger"
    if feature == "SCHEME_RAG":
        return "scheme_rag"
    # MEETING / TRAINING / AGRI / CATALOG nodes follow the same pattern —
    # stubbed here; add as services/orchestrator/nodes/<feature>_node.py and
    # register below. Keeping the graph the single source of truth for "what
    # features exist" is the whole point of this redesign.
    return "unhandled"


async def _unhandled_node(state: ConversationState) -> dict:
    msg = (
        "আমি হিসাব রাখতে, প্রকল্প জানাতে, আর পণ্যের "
        "বিজ্ঞাপন বানাতে পারি। কি দরকার আপনার?"
    )
    return {"outbound_messages": [{"type": "text", "body": msg}], "trace": ["unhandled_node"]}


def build_graph() -> StateGraph:
    graph = StateGraph(ConversationState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("ledger", ledger_extract_node)
    graph.add_node("scheme_rag", scheme_rag_node)
    graph.add_node("unhandled", _unhandled_node)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        _route_after_intent,
        {"ledger": "ledger", "scheme_rag": "scheme_rag", "unhandled": "unhandled"},
    )
    graph.add_edge("ledger", END)
    graph.add_edge("scheme_rag", END)
    graph.add_edge("unhandled", END)

    return graph


async def get_compiled_graph():
    """
    Compile with a Postgres checkpointer so conversation state survives
    process restarts and is queryable for debugging
    (`SELECT * FROM checkpoints WHERE thread_id = '<whatsapp_number>'`).
    """
    s = get_settings()
    async with AsyncPostgresSaver.from_conn_string(s.database_url) as checkpointer:
        await checkpointer.setup()
        graph = build_graph()
        return graph.compile(checkpointer=checkpointer)
