from celery import Celery
import asyncio
import logging

from services.orchestrator.graph import get_compiled_graph
from shared.whatsapp.sender import send_text
from shared.config.settings import get_settings

logger = logging.getLogger("celery_entrypoint")

s = get_settings()
celery_app = Celery("kotha_khata_orchestrator", broker=s.redis_url, backend=s.redis_url)
celery_app.conf.update(
    task_serializer="json", result_serializer="json", accept_content=["json"]
)


@celery_app.task(name="orchestrator.process_turn", max_retries=2, default_retry_delay=5)
def process_turn(whatsapp_number: str, turn_input: dict):
    asyncio.run(_process_turn_async(whatsapp_number, turn_input))


async def _process_turn_async(whatsapp_number: str, turn_input: dict):
    try:
        graph = await get_compiled_graph()
        config = {"configurable": {"thread_id": whatsapp_number}}
        state_update = {"whatsapp_number": whatsapp_number, **turn_input}
        result = await graph.ainvoke(state_update, config=config)
    except Exception:
        logger.exception("process_turn failed for %s", whatsapp_number)
        await send_text(whatsapp_number, "দুঃখিত, একটু সমস্যা হয়েছে। আবার চেষ্টা করুন।")
        return

    for msg in result.get("outbound_messages", []):
        try:
            if msg["type"] == "text":
                await send_text(whatsapp_number, msg["body"])
            elif msg["type"] == "document":
                from shared.whatsapp.sender import send_document

                await send_document(whatsapp_number, msg["url"], msg["filename"], msg.get("caption", ""))
            elif msg["type"] == "image":
                from shared.whatsapp.sender import send_image

                await send_image(whatsapp_number, msg["url"], msg.get("caption", ""))
        except Exception:
            logger.exception("failed to deliver one outbound message to %s", whatsapp_number)
