"""Unchanged from v1 — this was already solid, no architectural issue here."""
import httpx
from shared.config.settings import get_settings

WA_API = "https://graph.facebook.com/v19.0/{phone_id}/messages"


async def send_text(to: str, body: str) -> dict:
    s = get_settings()
    async with httpx.AsyncClient() as client:
        r = await client.post(
            WA_API.format(phone_id=s.wa_phone_number_id),
            headers={"Authorization": f"Bearer {s.wa_access_token}"},
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"body": body, "preview_url": False},
            },
        )
    return r.json()


async def send_document(to: str, url: str, filename: str, caption: str = "") -> dict:
    s = get_settings()
    async with httpx.AsyncClient() as client:
        r = await client.post(
            WA_API.format(phone_id=s.wa_phone_number_id),
            headers={"Authorization": f"Bearer {s.wa_access_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "document",
                "document": {"link": url, "filename": filename, "caption": caption},
            },
        )
    return r.json()


async def send_flow(to: str, flow_id: str, flow_cta: str, flow_token: str, screen: str) -> dict:
    """New in v2 — triggers a WhatsApp Flow (see whatsapp_flows/*.json)."""
    s = get_settings()
    async with httpx.AsyncClient() as client:
        r = await client.post(
            WA_API.format(phone_id=s.wa_phone_number_id),
            headers={"Authorization": f"Bearer {s.wa_access_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "body": {"text": "নিচের ফর্মটি পূরণ করুন"},
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_token": flow_token,
                            "flow_id": flow_id,
                            "flow_cta": flow_cta,
                            "flow_action": "navigate",
                            "flow_action_payload": {"screen": screen},
                        },
                    },
                },
            },
        )
    return r.json()
