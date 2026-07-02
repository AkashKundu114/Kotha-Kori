
import httpx

from shared.config.settings import get_settings

async def _download(media_id: str) -> bytes:
    s = get_settings()
    async with httpx.AsyncClient() as client:
        url_resp = await client.get(
            f"https://graph.facebook.com/v19.0/{media_id}",
            headers={"Authorization": f"Bearer {s.wa_access_token}"},
        )
        url_resp.raise_for_status()
        download_url = url_resp.json()["url"]
        media_resp = await client.get(download_url, headers={"Authorization": f"Bearer {s.wa_access_token}"})
        media_resp.raise_for_status()
        return media_resp.content

async def download_whatsapp_audio(media_id: str) -> bytes:
    return await _download(media_id)

async def download_whatsapp_image(media_id: str) -> bytes:
    return await _download(media_id)
