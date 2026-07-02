
from __future__ import annotations

import base64
import json
from enum import Enum

import httpx
import anthropic

from shared.config.settings import get_settings

CLAUDE_MODEL = "claude-sonnet-4-6"
CLAUDE_VISION_MODEL = "claude-sonnet-4-6"

class TaskCriticality(str, Enum):

    SAFETY_CRITICAL = "safety_critical"

    ROUTINE = "routine"

async def _call_local_qwen(system: str, prompt: str) -> tuple[str, float]:

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
        confidence = float(parsed.get("confidence", parsed.get("overall_confidence", 0.0)))
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return text, confidence

async def _call_claude(system: str, prompt: str, max_tokens: int = 800) -> str:
    s = get_settings()
    client = anthropic.AsyncAnthropic(api_key=s.anthropic_api_key)
    message = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in message.content if b.type == "text").strip()

async def route_completion(
    *,
    system: str,
    prompt: str,
    criticality: TaskCriticality,
    confidence_floor: float = 0.80,
) -> dict:

    if criticality == TaskCriticality.SAFETY_CRITICAL:
        text = await _call_claude(system, prompt)
        return {"text": text, "model_used": "claude", "escalated": False}

    text, local_confidence = await _call_local_qwen(system, prompt)
    if local_confidence >= confidence_floor:
        return {"text": text, "model_used": "qwen-local", "escalated": False}

    text = await _call_claude(system, prompt)
    return {"text": text, "model_used": "claude", "escalated": True}

async def _call_local_vision(prompt: str, image_bytes: bytes) -> tuple[str, bool]:

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

async def _call_claude_vision(prompt: str, image_bytes: bytes, media_type: str = "image/jpeg") -> str:
    s = get_settings()
    client = anthropic.AsyncAnthropic(api_key=s.anthropic_api_key)
    image_b64 = base64.b64encode(image_bytes).decode()
    message = await client.messages.create(
        model=CLAUDE_VISION_MODEL,
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return "".join(b.text for b in message.content if b.type == "text").strip()

async def route_vision_completion(*, prompt: str, image_bytes: bytes, criticality: TaskCriticality) -> dict:

    if criticality == TaskCriticality.SAFETY_CRITICAL:
        text = await _call_claude_vision(prompt, image_bytes)
        return {"text": text, "model_used": "claude-vision", "escalated": False}

    text, ok = await _call_local_vision(prompt, image_bytes)
    if ok:
        return {"text": text, "model_used": "ollama-qwen2vl", "escalated": False}

    text = await _call_claude_vision(prompt, image_bytes)
    return {"text": text, "model_used": "claude-vision", "escalated": True}
