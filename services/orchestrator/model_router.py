"""
Model cascade: route each LLM call to the cheapest model that can be trusted
for that task, escalating to Claude when criticality or confidence demands it.

This replaces the v1 binary choice (all-Claude during MVP, all-self-hosted
post-pilot) with per-call routing, so cost and quality are both optimized at
every stage instead of trading one for the other on a fixed migration date.
"""
from __future__ import annotations

import json
from enum import Enum

import httpx
import anthropic

from shared.config.settings import get_settings

CLAUDE_MODEL = "claude-sonnet-4-6"


class TaskCriticality(str, Enum):
    # Wrong output has real-world consequences for the user (money, eligibility).
    # Always goes to Claude. Never silently downgraded.
    SAFETY_CRITICAL = "safety_critical"

    # High-volume, low-stakes, well-specified extraction. Self-hosted by default;
    # escalates to Claude only if the local model's confidence is low.
    ROUTINE = "routine"


async def _call_local_qwen(system: str, prompt: str) -> tuple[str, float]:
    """Call the self-hosted fine-tuned Qwen2.5-7B via Ollama. Returns (text, self_reported_confidence)."""
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

    # The fine-tuning dataset trains the model to emit a trailing confidence field
    # for routine extraction tasks, e.g. {"...", "confidence": 0.91}. If absent,
    # treat as low-confidence so we escalate rather than guess.
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
    """
    Returns: {"text": str, "model_used": "claude" | "qwen-local", "escalated": bool}
    """
    if criticality == TaskCriticality.SAFETY_CRITICAL:
        text = await _call_claude(system, prompt)
        return {"text": text, "model_used": "claude", "escalated": False}

    # ROUTINE — try local first.
    text, local_confidence = await _call_local_qwen(system, prompt)
    if local_confidence >= confidence_floor:
        return {"text": text, "model_used": "qwen-local", "escalated": False}

    # Local model wasn't confident — escalate rather than ship a guess.
    text = await _call_claude(system, prompt)
    return {"text": text, "model_used": "claude", "escalated": True}
