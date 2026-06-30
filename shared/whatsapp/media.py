"""Download voice-note / image bytes from Meta's media API given a media id."""
import httpx

from shared.config.settings import get_settings


async def download_whatsapp_audio(media_id: str) -> bytes:
    s = get_settings()
    async with httpx.AsyncClient() as client:
        url_resp = await client.get(
            f"https://graph.facebook.com/v19.0/{media_id}",
            headers={"Authorization": f"Bearer {s.wa_access_token}"},
        )
        download_url = url_resp.json()["url"]
        audio_resp = await client.get(download_url, headers={"Authorization": f"Bearer {s.wa_access_token}"})
        return audio_resp.content
