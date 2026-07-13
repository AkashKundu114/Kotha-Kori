from __future__ import annotations

import base64

import httpx

from shared.config.settings import get_settings

_TIMEOUT = 20.0


class SarvamUnavailableError(Exception):
    pass


def _headers(s) -> dict:
    return {"api-subscription-key": s.sarvam_api_key, "Content-Type": "application/json"}


async def translate(text: str, target_lang: str, source_lang: str = "auto") -> str:
    s = get_settings()
    if not s.sarvam_api_key:
        raise SarvamUnavailableError("SARVAM_API_KEY not configured")

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                f"{s.sarvam_base_url}/translate",
                headers=_headers(s),
                json={
                    "input": text,
                    "source_language_code": source_lang,
                    "target_language_code": target_lang,
                },
            )
            r.raise_for_status()
            body = r.json()
        return (body.get("translated_text") or "").strip()
    except Exception as exc:
        raise SarvamUnavailableError(str(exc)) from exc


async def chat_completion(system: str, prompt: str, model: str | None = None, max_tokens: int = 700) -> str:
    s = get_settings()
    if not s.sarvam_api_key:
        raise SarvamUnavailableError("SARVAM_API_KEY not configured")

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                f"{s.sarvam_base_url}/chat/completions",
                headers=_headers(s),
                json={
                    "model": model or s.sarvam_chat_model,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            r.raise_for_status()
            body = r.json()
        return (body["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:
        raise SarvamUnavailableError(str(exc)) from exc


async def vision_completion(prompt: str, image_bytes: bytes, max_tokens: int = 600) -> str:
    s = get_settings()
    if not s.sarvam_api_key:
        raise SarvamUnavailableError("SARVAM_API_KEY not configured")

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                f"{s.sarvam_base_url}/vision/completions",
                headers=_headers(s),
                json={
                    "model": s.sarvam_vision_model,
                    "max_tokens": max_tokens,
                    "prompt": prompt,
                    "image": base64.b64encode(image_bytes).decode(),
                },
            )
            r.raise_for_status()
            body = r.json()
        return (body.get("text") or body.get("choices", [{}])[0].get("message", {}).get("content", "") or "").strip()
    except Exception as exc:
        raise SarvamUnavailableError(str(exc)) from exc


async def chat_completion_self_hosted(system: str, prompt: str, max_tokens: int = 700) -> str:
    s = get_settings()
    if not s.sarvam_local_base_url:
        raise SarvamUnavailableError("SARVAM_LOCAL_BASE_URL not configured")

    from openai import AsyncOpenAI

    try:
        client = AsyncOpenAI(base_url=s.sarvam_local_base_url, api_key="not-needed", timeout=30.0, max_retries=0)
        response = await client.chat.completions.create(
            model=s.sarvam_chat_model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        raise SarvamUnavailableError(str(exc)) from exc
