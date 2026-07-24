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
from services.orchestrator.nodes.pricing_node import pricing_node
from services.orchestrator.nodes.negotiation_node import negotiation_node
from services.orchestrator.nodes.conversation_node import general_conversation_node
from shared.config.settings import get_settings


def _route_after_profile_load(state: ConversationState) -> str:
    if state.get("is_new_user") or (
        state.get("onboarding_step") and state["onboarding_step"] != "DONE"
    ):
        return "onboarding"
    if state.get("awaiting_confirmation"):
        return "ledger_confirm"
    if state.get("awaiting_negotiation"):
        return "negotiation"
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
    if feature == "PRICING":
        return "pricing"
    if feature == "NEGOTIATION":
        return "negotiation"
    return "unhandled"


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
    graph.add_node("pricing", pricing_node)
    graph.add_node("negotiation", negotiation_node)
    graph.add_node("unhandled", general_conversation_node)

    graph.set_entry_point("load_user_profile")
    graph.add_conditional_edges(
        "load_user_profile",
        _route_after_profile_load,
        {
            "onboarding": "onboarding",
            "ledger_confirm": "ledger_confirm",
            "negotiation": "negotiation",
            "catalog": "catalog",
            "classify_intent": "classify_intent",
        },
    )
    graph.add_conditional_edges(
        "classify_intent",
        _route_after_intent,
        {
            "ledger": "ledger",
            "ledger_report": "ledger_report",
            "market": "market",
            "pricing": "pricing",
            "negotiation": "negotiation",
            "unhandled": "unhandled",
        },
    )
    graph.add_edge("onboarding", END)
    graph.add_edge("ledger", END)
    graph.add_edge("ledger_confirm", END)
    graph.add_edge("ledger_report", END)
    graph.add_edge("catalog", END)
    graph.add_edge("market", END)
    graph.add_edge("pricing", END)
    graph.add_edge("negotiation", END)
    graph.add_edge("unhandled", END)

    return graph


_compiled_graph = None


async def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph

    s = get_settings()
    checkpointer_ctx = AsyncPostgresSaver.from_conn_string(s.database_url)
    checkpointer = await checkpointer_ctx.__aenter__()
    await checkpointer.setup()
    graph = build_graph()
    _compiled_graph = graph.compile(checkpointer=checkpointer)
    return _compiled_graph
