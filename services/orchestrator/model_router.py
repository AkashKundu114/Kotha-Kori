from __future__ import annotations

import base64
import json
from enum import Enum

import httpx
from openai import AsyncOpenAI

from shared.config.settings import get_settings


class TaskCriticality(str, Enum):
    SAFETY_CRITICAL = "safety_critical"

    ROUTINE = "routine"


def _openai_client() -> AsyncOpenAI:
    s = get_settings()
    return AsyncOpenAI(api_key=s.openai_api_key)


async def _call_local_qwen(system: str, prompt: str) -> tuple[str, float]:
    """Only used if OLLAMA/local models are actually deployed (use_local_models=True
    in settings). On a GPU-less DO deployment this is skipped entirely so a routine
    call never wastes a 30s timeout waiting on a host that was never provisioned."""

    s = get_settings()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{s.ollama_base_url}/api/generate",
            json={
                "model": s.ollama_llm_model,
                "system": system,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 512},
            },
        )
        text = r.json()["response"].strip()

    confidence = 0.0
    try:
        parsed = json.loads(text)
        confidence = float(
            parsed.get("confidence", parsed.get("overall_confidence", 0.0))
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return text, confidence


async def _call_openai(system: str, prompt: str, max_tokens: int = 800) -> str:
    s = get_settings()
    client = _openai_client()
    response = await client.chat.completions.create(
        model=s.openai_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


async def route_completion(
    *,
    system: str,
    prompt: str,
    criticality: TaskCriticality,
    confidence_floor: float = 0.80,
) -> dict:
    if criticality == TaskCriticality.SAFETY_CRITICAL:
        text = await _call_openai(system, prompt)
        return {"text": text, "model_used": "openai", "escalated": False}

    s = get_settings()
    if s.use_local_models:
        text, local_confidence = await _call_local_qwen(system, prompt)
        if local_confidence >= confidence_floor:
            return {"text": text, "model_used": "qwen-local", "escalated": False}

    text = await _call_openai(system, prompt)
    return {"text": text, "model_used": "openai", "escalated": True}


async def _call_local_vision(prompt: str, image_bytes: bytes) -> tuple[str, bool]:
    """Only used if use_local_models=True — see _call_local_qwen note above."""

    s = get_settings()
    image_b64 = base64.b64encode(image_bytes).decode()
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                f"{s.ollama_base_url}/api/generate",
                json={
                    "model": s.ollama_vision_model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                },
            )
            r.raise_for_status()
            text = r.json().get("response", "").strip()
            return text, bool(text)
    except (httpx.HTTPError, KeyError, ValueError):
        return "", False


async def _call_openai_vision(
    prompt: str, image_bytes: bytes, media_type: str = "image/jpeg"
) -> str:
    s = get_settings()
    client = _openai_client()
    image_b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:{media_type};base64,{image_b64}"
    response = await client.chat.completions.create(
        model=s.openai_vision_model,
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    )
    return (response.choices[0].message.content or "").strip()


async def route_vision_completion(
    *, prompt: str, image_bytes: bytes, criticality: TaskCriticality
) -> dict:
    if criticality == TaskCriticality.SAFETY_CRITICAL:
        text = await _call_openai_vision(prompt, image_bytes)
        return {"text": text, "model_used": "openai-vision", "escalated": False}

    s = get_settings()
    if s.use_local_models:
        text, ok = await _call_local_vision(prompt, image_bytes)
        if ok:
            return {"text": text, "model_used": "ollama-qwen2vl", "escalated": False}

    text = await _call_openai_vision(prompt, image_bytes)
    return {"text": text, "model_used": "openai-vision", "escalated": True}
