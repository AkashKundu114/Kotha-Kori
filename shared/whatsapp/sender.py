import logging

import httpx

from shared.config.settings import get_settings

logger = logging.getLogger("whatsapp_sender")

WA_API = "https://graph.facebook.com/v19.0/{phone_id}/messages"
_TIMEOUT = 15.0


async def _post(payload: dict) -> dict:
    """All sends go through here so failures are logged once, in one place,
    and never raise into a caller that might crash a Celery task over a
    transient WhatsApp API hiccup."""
    s = get_settings()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                WA_API.format(phone_id=s.wa_phone_number_id),
                headers={"Authorization": f"Bearer {s.wa_access_token}"},
                json=payload,
            )
            if r.status_code >= 400:
                logger.warning("whatsapp send failed: %s %s", r.status_code, r.text[:500])
            return r.json()
    except Exception as exc:
        logger.error("whatsapp send raised: %s", exc)
        return {"error": str(exc)}


async def send_text(to: str, body: str) -> dict:
    return await _post(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": body[:4096], "preview_url": False},
        }
    )


async def send_document(to: str, url: str, filename: str, caption: str = "") -> dict:
    return await _post(
        {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {"link": url, "filename": filename, "caption": caption[:1024]},
        }
    )


async def send_image(to: str, url: str, caption: str = "") -> dict:
    return await _post(
        {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "image",
            "image": {"link": url, "caption": caption[:1024]},
        }
    )
