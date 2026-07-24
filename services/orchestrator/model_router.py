from __future__ import annotations

import base64
import json
import logging
from enum import Enum

import httpx

from shared.config.settings import get_settings
from services.translation_service import sarvam_client
from services.translation_service.sarvam_client import SarvamUnavailableError

logger = logging.getLogger("model_router")


class TaskCriticality(str, Enum):
    SAFETY_CRITICAL = "safety_critical"
    ROUTINE = "routine"


class AgentTier(str, Enum):

    STANDARD = "standard"
    ADVANCED = "advanced"


class ModelUnavailableError(Exception):
    pass


def _parse_self_reported_confidence(text: str) -> float:
    try:
        parsed = json.loads(text)
        return float(parsed.get("confidence", parsed.get("overall_confidence", 0.0)))
    except (json.JSONDecodeError, TypeError, ValueError):
        return 0.0


async def _call_local_ollama(system: str, prompt: str) -> tuple[str, float]:
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


async def route_completion(
    *,
    system: str,
    prompt: str,
    criticality: TaskCriticality,
    tier: AgentTier = AgentTier.STANDARD,
    confidence_floor: float = 0.80,
) -> dict:
    s = get_settings()
    model_name = s.sarvam_advanced_model if tier == AgentTier.ADVANCED else s.sarvam_chat_model

    if s.sarvam_api_key:
        try:
            text = await sarvam_client.chat_completion(system, prompt, model=model_name)
            if _parse_self_reported_confidence(text) >= confidence_floor:
                return {"text": text, "model_used": f"sarvam-{tier.value}", "escalated": False}
            logger.warning("Sarvam (%s) low self-reported confidence, falling through to local", tier.value)
        except SarvamUnavailableError as exc:
            logger.warning("Sarvam (%s) unavailable, falling through to local: %s", tier.value, exc)

    if s.use_local_models:
        try:
            text, local_confidence = await _call_local_ollama(system, prompt)
            if local_confidence >= confidence_floor:
                return {"text": text, "model_used": "ollama-local", "escalated": True}
            logger.warning("local Ollama low self-reported confidence (%.2f)", local_confidence)
            return {"text": text, "model_used": "ollama-local", "escalated": True}
        except Exception as exc:
            logger.error("local Ollama unavailable: %s", exc)
            raise ModelUnavailableError(str(exc)) from exc

    raise ModelUnavailableError(
        "Sarvam unavailable/unconfigured and USE_LOCAL_MODELS is false - no fallback tier configured"
    )


async def route_translation(text: str, target_lang: str, source_lang: str = "auto") -> dict:
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
            logger.warning("self-hosted translation box unavailable, falling through: %s", exc)

    if s.use_local_models:
        try:
            text_out, _ = await _call_local_ollama(
                system=f"Translate the user's message to {target_lang}. Reply with only the translation, nothing else.",
                prompt=text,
            )
            if text_out:
                return {"text": text_out, "model_used": "ollama-local"}
        except Exception as exc:
            logger.error("local Ollama translation failed: %s", exc)

    raise ModelUnavailableError("no translation tier available (Sarvam and local Ollama both failed/unconfigured)")


async def _call_local_vision(prompt: str, image_bytes: bytes) -> tuple[str, bool]:
    s = get_settings()
    image_b64 = base64.b64encode(image_bytes).decode()
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                f"{s.ollama_base_url}/api/generate",
                json={"model": s.ollama_vision_model, "prompt": prompt, "images": [image_b64], "stream": False},
            )
            r.raise_for_status()
            text = r.json().get("response", "").strip()
            return text, bool(text)
    except (httpx.HTTPError, KeyError, ValueError):
        return "", False


async def route_vision_completion(*, prompt: str, image_bytes: bytes, criticality: TaskCriticality) -> dict:
    s = get_settings()

    if s.sarvam_api_key:
        try:
            text = await sarvam_client.vision_completion(prompt, image_bytes)
            if text:
                return {"text": text, "model_used": "sarvam-vision", "escalated": False}
        except SarvamUnavailableError as exc:
            logger.warning("Sarvam Vision unavailable, falling through to local: %s", exc)

    if s.use_local_models:
        text, ok = await _call_local_vision(prompt, image_bytes)
        if ok:
            return {"text": text, "model_used": "ollama-vision", "escalated": True}

    raise ModelUnavailableError(
        "no vision tier available (Sarvam Vision failed/unconfigured, local vision not enabled)"
    )
