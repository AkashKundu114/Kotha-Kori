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
    SAFETY_CRITICAL = "safety_critical"  # reserved for scheme-eligibility-style answers
    ROUTINE = "routine"


class AgentTier(str, Enum):
    """Which Sarvam model tier an agent should use. Everything still falls
    back to local Ollama if this tier is unavailable — see route_completion.
    Advanced-tier calls never silently downgrade to the standard Sarvam
    model on failure; they go straight to the free local fallback, so a
    tier mix-up never changes output quality without anyone noticing."""

    STANDARD = "standard"   # sarvam-30b: ledger, market phrasing, conversation, pricing
    ADVANCED = "advanced"   # sarvam-105b: ads, negotiation


class ModelUnavailableError(Exception):
    """Raised when every configured tier — paid Sarvam AND the free local
    fallback — has failed or is unconfigured. Callers (orchestrator nodes)
    must catch this and return a friendly Bengali message — never let it
    propagate uncaught into the graph.

    NOTE: as of the OpenAI removal, there is no third "always eventually
    works" paid tier. If Sarvam is down and USE_LOCAL_MODELS=false, this
    fires immediately — see docs/architecture.md §8."""


def _parse_self_reported_confidence(text: str) -> float:
    """Every ROUTINE prompt in this codebase asks the model to include a
    'confidence' field in its JSON output. Reused across every tier
    (Sarvam, local Ollama) to decide whether to trust the result."""
    try:
        parsed = json.loads(text)
        return float(parsed.get("confidence", parsed.get("overall_confidence", 0.0)))
    except (json.JSONDecodeError, TypeError, ValueError):
        return 0.0


async def _call_local_ollama(system: str, prompt: str) -> tuple[str, float]:
    """Free, self-hosted — the ONLY fallback tier now that OpenAI is gone.
    Requires USE_LOCAL_MODELS=true and a reachable Ollama box."""
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
    """Two-tier cascade for every text agent (ledger, pricing, market
    phrasing, conversation, government schemes, ads, negotiation):

      1. Sarvam (sarvam-30b or sarvam-105b, chosen via `tier`) — primary
         whenever SARVAM_API_KEY is set.
      2. Local Ollama — free, self-hosted, the ONLY fallback. If this isn't
         enabled/reachable and Sarvam fails, the call raises
         ModelUnavailableError and the node degrades to a Bengali error
         message. There is no third paid tier.

    `criticality` is retained for future use (e.g. re-enabling Scheme RAG
    with a stricter routing path) but does not currently change vendor
    selection — both tiers already go through the same two steps.
    """
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
            # Still return it — this is the last tier, a low-confidence local
            # answer beats raising and leaving the user with nothing.
            return {"text": text, "model_used": "ollama-local", "escalated": True}
        except Exception as exc:
            logger.error("local Ollama unavailable: %s", exc)
            raise ModelUnavailableError(str(exc)) from exc

    raise ModelUnavailableError(
        "Sarvam unavailable/unconfigured and USE_LOCAL_MODELS is false — no fallback tier configured"
    )


async def route_translation(text: str, target_lang: str, source_lang: str = "auto") -> dict:
    """Bengali<->English translation/normalization. Sarvam's dedicated
    /translate endpoint is tried first, then your own self-hosted
    sarvam-translate box (if configured), then generic local Ollama asked
    to translate via a plain prompt as the final free fallback."""
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
    """Sarvam Vision primary, local Ollama vision model (qwen2-vl) as the
    ONLY fallback — no paid final tier.

    OPEN VERIFICATION ITEM: Sarvam Vision's product-photo capability (vs.
    document/OCR-only) has not been confirmed against current Sarvam docs.
    Verify this before trusting it as the catalog-vision primary in
    production; if it turns out to be OCR/document-only, treat the Ollama
    tier as the real primary and set USE_LOCAL_MODELS=true accordingly."""
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
