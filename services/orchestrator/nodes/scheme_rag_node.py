from __future__ import annotations

from services.orchestrator.state import ConversationState
from services.rag_service.pipeline import query_scheme_rag
from services.rag_service.grounding_verifier import verify_grounding

FALLBACK_BENGALI = "এ বিষয়ে নিশ্চিত তথ্য নেই। পঞ্চায়েত অফিসে জিজ্ঞেস করুন।"

async def scheme_rag_node(state: ConversationState) -> dict:
    query = state.get("scheme_query") or state.get("raw_input_text") or state.get("raw_input_transcript") or ""

    rag_result = await query_scheme_rag(
        query=query,
        user_context={"whatsapp_number": state.get("whatsapp_number")},
        scheme_filter=state.get("scheme_filter"),
    )

    grounding = verify_grounding(
        answer_bengali=rag_result["answer_bengali"],
        retrieved_chunks=rag_result["citations_full"],
    )

    if grounding["all_grounded"]:
        final_answer = rag_result["answer_bengali"]
    else:

        final_answer = FALLBACK_BENGALI

    return {
        "retrieved_chunks": rag_result["citations_full"],
        "draft_answer_bengali": rag_result["answer_bengali"],
        "grounding_report": grounding,
        "final_answer_bengali": final_answer,
        "outbound_messages": [{"type": "text", "body": final_answer}],
        "trace": [f"scheme_rag_node:grounded={grounding['all_grounded']}"],
    }
