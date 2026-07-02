
from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from services.orchestrator.state import ConversationState
from services.orchestrator.nodes.user_profile_node import load_user_profile_node
from services.orchestrator.nodes.onboarding_node import onboarding_node
from services.orchestrator.nodes.intent_router import classify_intent
from services.orchestrator.nodes.ledger_node import ledger_extract_node
from services.orchestrator.nodes.ledger_confirm_node import ledger_confirm_node
from services.orchestrator.nodes.ledger_report_node import ledger_report_node
from services.orchestrator.nodes.catalog_node import catalog_node
from services.orchestrator.nodes.market_predictor_node import market_predictor_node
from shared.config.settings import get_settings

def _route_after_profile_load(state: ConversationState) -> str:

    if state.get("is_new_user") or (state.get("onboarding_step") and state["onboarding_step"] != "DONE"):
        return "onboarding"
    if state.get("awaiting_confirmation"):
        return "ledger_confirm"
    if state.get("last_message_type") == "image":
        return "catalog"
    return "classify_intent"

def _route_after_intent(state: ConversationState) -> str:
    feature = state.get("active_feature", "IDLE")
    if feature == "LEDGER":
        return "ledger"
    if feature == "LEDGER_REPORT":
        return "ledger_report"
    if feature == "MARKET":
        return "market"
    return "unhandled"

async def _unhandled_node(state: ConversationState) -> dict:
    msg = (
        "আমি হিসাব রাখতে, পণ্যের বিজ্ঞাপন বানাতে, আর বাজারের "
        "পরামর্শ দিতে পারি। কি দরকার আপনার?"
    )
    return {"outbound_messages": [{"type": "text", "body": msg}], "trace": ["unhandled_node"]}

def build_graph() -> StateGraph:
    graph = StateGraph(ConversationState)

    graph.add_node("load_user_profile", load_user_profile_node)
    graph.add_node("onboarding", onboarding_node)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("ledger", ledger_extract_node)
    graph.add_node("ledger_confirm", ledger_confirm_node)
    graph.add_node("ledger_report", ledger_report_node)
    graph.add_node("catalog", catalog_node)
    graph.add_node("market", market_predictor_node)
    graph.add_node("unhandled", _unhandled_node)

    graph.set_entry_point("load_user_profile")
    graph.add_conditional_edges(
        "load_user_profile",
        _route_after_profile_load,
        {
            "onboarding": "onboarding",
            "ledger_confirm": "ledger_confirm",
            "catalog": "catalog",
            "classify_intent": "classify_intent",
        },
    )
    graph.add_conditional_edges(
        "classify_intent",
        _route_after_intent,
        {"ledger": "ledger", "ledger_report": "ledger_report", "market": "market", "unhandled": "unhandled"},
    )
    graph.add_edge("onboarding", END)
    graph.add_edge("ledger", END)
    graph.add_edge("ledger_confirm", END)
    graph.add_edge("ledger_report", END)
    graph.add_edge("catalog", END)
    graph.add_edge("market", END)
    graph.add_edge("unhandled", END)

    return graph

async def get_compiled_graph():
    s = get_settings()
    async with AsyncPostgresSaver.from_conn_string(s.database_url) as checkpointer:
        await checkpointer.setup()
        graph = build_graph()
        return graph.compile(checkpointer=checkpointer)
