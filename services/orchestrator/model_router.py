from __future__ import annotations

import base64
import json
import logging
from enum import Enum

import httpx
from openai import AsyncOpenAI

from shared.config.settings import get_settings
from services.translation_service import sarvam_client
from services.translation_service.sarvam_client import SarvamUnavailableError

logger = logging.getLogger("model_router")

_REQUEST_TIMEOUT = 25.0
_SDK_MAX_RETRIES = 2  # OpenAI SDK's own built-in retry-with-backoff


class TaskCriticality(str, Enum):
    SAFETY_CRITICAL = "safety_critical"  # bypasses Sarvam entirely, goes straight to OpenAI
    ROUTINE = "routine"


class ModelUnavailableError(Exception):
    """Raised when every configured model tier has failed. Callers (orchestrator
    nodes) must catch this and return a friendly Bengali message — never let it
    propagate uncaught into the graph."""


def _openai_client() -> AsyncOpenAI:
    s = get_settings()
    return AsyncOpenAI(api_key=s.openai_api_key, timeout=_REQUEST_TIMEOUT, max_retries=_SDK_MAX_RETRIES)


def _parse_self_reported_confidence(text: str) -> float:
    """Every ROUTINE prompt in this codebase asks the model to include a
    'confidence' field in its JSON output. Reused across every cheap-tier
    caller (Sarvam, local Qwen) to decide whether to trust the result or
    escalate to OpenAI."""
    try:
        parsed = json.loads(text)
        return float(parsed.get("confidence", parsed.get("overall_confidence", 0.0)))
    except (json.JSONDecodeError, TypeError, ValueError):
        return 0.0


async def _call_local_qwen(system: str, prompt: str) -> tuple[str, float]:
    """Only used if USE_LOCAL_MODELS=true and an Ollama box is actually running.
    Free, self-hosted — not a third-party API."""
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
        r.raise_for_status()
        text = r.json()["response"].strip()
    return text, _parse_self_reported_confidence(text)


async def _call_openai(system: str, prompt: str, max_tokens: int = 700) -> str:
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
    """Three-tier cost cascade for ROUTINE text tasks (ledger extraction,
    corrections, market phrasing, captions, off-topic conversation):

      1. Sarvam (sarvam-30b) — cheap, Indic-native. Primary tier whenever
         SARVAM_API_KEY is set. This is where most spend should land.
      2. Self-hosted local model (Ollama or your own Sarvam box) — free,
         opt-in via USE_LOCAL_MODELS / SARVAM_LOCAL_BASE_URL.
      3. OpenAI (gpt-4o-mini) — quality escalation and final fallback.

    A cheap tier's own self-reported 'confidence' field gates whether its
    output is trusted or the next tier is tried — same pattern regardless
    of which tier produced it.

    SAFETY_CRITICAL bypasses tiers 1–2 entirely and goes straight to OpenAI —
    reserved for any future feature (e.g. re-enabled scheme eligibility)
    where a wrong answer has real consequences and cost is not the concern.
    """
    s = get_settings()

    if criticality == TaskCriticality.ROUTINE:
        if s.sarvam_api_key:
            try:
                text = await sarvam_client.chat_completion(system, prompt)
                if _parse_self_reported_confidence(text) >= confidence_floor:
                    return {"text": text, "model_used": "sarvam", "escalated": False}
            except SarvamUnavailableError as exc:
                logger.warning("Sarvam unavailable, falling through: %s", exc)

        if s.use_local_models:
            try:
                text, local_confidence = await _call_local_qwen(system, prompt)
                if local_confidence >= confidence_floor:
                    return {"text": text, "model_used": "qwen-local", "escalated": True}
            except Exception as exc:
                logger.warning("local model unavailable, falling through to OpenAI: %s", exc)

    try:
        text = await _call_openai(system, prompt)
        escalated = criticality == TaskCriticality.ROUTINE and (bool(s.sarvam_api_key) or s.use_local_models)
        return {"text": text, "model_used": "openai", "escalated": escalated}
    except Exception as exc:
        logger.error("OpenAI call failed after retries: %s", exc)
        raise ModelUnavailableError(str(exc)) from exc


async def route_translation(text: str, target_lang: str, source_lang: str = "auto") -> dict:
    """Bengali<->English translation/normalization. Sarvam's dedicated /translate
    endpoint is purpose-built and cheaper than asking a chat model to translate,
    so it's tried first regardless of USE_LOCAL_MODELS. Falls back to your
    self-hosted box, then to OpenAI as a last resort (asked to translate via
    a plain chat prompt, since it has no dedicated MT endpoint)."""
    s = get_settings()

    if s.sarvam_api_key:
        try:
            translated = await sarvam_client.translate(text, target_lang=target_lang, source_lang=source_lang)
            if translated:
                return {"text": translated, "model_used": "sarvam-translate"}
        except SarvamUnavailableError as exc:
            logger.warning("Sarvam translate unavailable, falling through: %s", exc)

    if s.sarvam_local_base_url:
        try:
            translated = await sarvam_client.chat_completion_self_hosted(
                system=f"Translate the user's message to {target_lang}. Reply with only the translation, nothing else.",
                prompt=text,
                max_tokens=300,
            )
            if translated:
                return {"text": translated, "model_used": "sarvam-local"}
        except SarvamUnavailableError as exc:
            logger.warning("self-hosted translation unavailable, falling through to OpenAI: %s", exc)

    try:
        translated = await _call_openai(
            system=f"Translate the user's message to {target_lang}. Reply with only the translation, nothing else.",
            prompt=text,
            max_tokens=300,
        )
        return {"text": translated, "model_used": "openai"}
    except Exception as exc:
        logger.error("Translation failed on every tier: %s", exc)
        raise ModelUnavailableError(str(exc)) from exc


async def _call_local_vision(prompt: str, image_bytes: bytes) -> tuple[str, bool]:
    s = get_settings()
    image_b64 = base64.b64encode(image_bytes).decode()
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                f"{s.ollama_base_url}/api/generate",
                json={"model": s.ollama_llm_model, "prompt": prompt, "images": [image_b64], "stream": False},
            )
            r.raise_for_status()
            text = r.json().get("response", "").strip()
            return text, bool(text)
    except (httpx.HTTPError, KeyError, ValueError):
        return "", False


async def _call_openai_vision(prompt: str, image_bytes: bytes, media_type: str = "image/jpeg") -> str:
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


async def route_vision_completion(*, prompt: str, image_bytes: bytes, criticality: TaskCriticality) -> dict:
    """Vision stays OpenAI-only by design — Sarvam has no general product-photo
    vision model (Sarvam Vision is document/OCR intelligence, a different tool
    for a different job). The optional local tier is a generic Ollama
    vision-capable model if you've configured one, not Sarvam-specific."""
    s = get_settings()

    if s.use_local_models:
        try:
            text, ok = await _call_local_vision(prompt, image_bytes)
            if ok:
                return {"text": text, "model_used": "ollama-vision", "escalated": False}
        except Exception as exc:
            logger.warning("local vision unavailable, falling through to OpenAI: %s", exc)

    try:
        text = await _call_openai_vision(prompt, image_bytes)
        return {"text": text, "model_used": "openai-vision", "escalated": s.use_local_models}
    except Exception as exc:
        logger.error("OpenAI vision call failed after retries: %s", exc)
        raise ModelUnavailableError(str(exc)) from exc
