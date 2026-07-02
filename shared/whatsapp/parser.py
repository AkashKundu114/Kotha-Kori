from dataclasses import dataclass
from typing import Optional, Literal

@dataclass
class IncomingMessage:
    message_id: str
    from_number: str
    timestamp: int
    message_type: Literal["text", "audio", "image", "document", "interactive"]
    text: Optional[str] = None
    audio_id: Optional[str] = None
    audio_mime_type: Optional[str] = None
    image_id: Optional[str] = None
    caption: Optional[str] = None
    interactive_payload: Optional[dict] = None

def parse_webhook_payload(payload: dict) -> Optional[IncomingMessage]:
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]["value"]
        if "messages" not in change:
            return None

        msg = change["messages"][0]
        base = IncomingMessage(
            message_id=msg["id"],
            from_number=msg["from"],
            timestamp=int(msg["timestamp"]),
            message_type=msg["type"],
        )

        if msg["type"] == "text":
            base.text = msg["text"]["body"]
        elif msg["type"] == "audio":
            base.audio_id = msg["audio"]["id"]
            base.audio_mime_type = msg["audio"]["mime_type"]
        elif msg["type"] == "image":
            base.image_id = msg["image"]["id"]
            base.caption = msg.get("image", {}).get("caption")
        elif msg["type"] == "interactive" and msg["interactive"].get("type") == "nfm_reply":
            import json

            base.interactive_payload = json.loads(msg["interactive"]["nfm_reply"]["response_json"])

        return base
    except (KeyError, IndexError):
        return None
