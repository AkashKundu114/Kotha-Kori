
from celery import Celery
import asyncio

from services.orchestrator.graph import get_compiled_graph
from shared.whatsapp.sender import send_text
from shared.config.settings import get_settings

s = get_settings()
celery_app = Celery("kotha_khata_orchestrator", broker=s.redis_url, backend=s.redis_url)

@celery_app.task(name="orchestrator.process_turn", max_retries=2, default_retry_delay=5)
def process_turn(whatsapp_number: str, turn_input: dict):
    asyncio.run(_process_turn_async(whatsapp_number, turn_input))

async def _process_turn_async(whatsapp_number: str, turn_input: dict):
    graph = await get_compiled_graph()
    config = {"configurable": {"thread_id": whatsapp_number}}

    state_update = {"whatsapp_number": whatsapp_number, **turn_input}
    result = await graph.ainvoke(state_update, config=config)

    for msg in result.get("outbound_messages", []):
        if msg["type"] == "text":
            await send_text(whatsapp_number, msg["body"])
