import httpx

from shared.config.settings import get_settings

MAX_AUDIO_BYTES = 6 * 1024 * 1024  
MAX_IMAGE_BYTES = 5 * 1024 * 1024


class MediaTooLargeError(Exception):
    pass


async def _download(media_id: str, max_bytes: int | None = None) -> bytes:
    s = get_settings()
    async with httpx.AsyncClient(timeout=15.0) as client:
        url_resp = await client.get(
            f"https://graph.facebook.com/v19.0/{media_id}",
            headers={"Authorization": f"Bearer {s.wa_access_token}"},
        )
        url_resp.raise_for_status()
        meta = url_resp.json()

        reported_size = meta.get("file_size")
        if max_bytes and reported_size is not None:
            try:
                if int(reported_size) > max_bytes:
                    raise MediaTooLargeError(
                        f"media_id={media_id} reported file_size={reported_size} exceeds cap={max_bytes}"
                    )
            except (TypeError, ValueError):
                pass

        download_url = meta["url"]
        media_resp = await client.get(
            download_url, headers={"Authorization": f"Bearer {s.wa_access_token}"}
        )
        media_resp.raise_for_status()

        if max_bytes and len(media_resp.content) > max_bytes:
            raise MediaTooLargeError(
                f"media_id={media_id} downloaded size={len(media_resp.content)} exceeds cap={max_bytes}"
            )

        return media_resp.content


async def download_whatsapp_audio(media_id: str) -> bytes:
    return await _download(media_id, max_bytes=MAX_AUDIO_BYTES)


async def download_whatsapp_image(media_id: str) -> bytes:
    return await _download(media_id, max_bytes=MAX_IMAGE_BYTES)
