from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # --- WhatsApp Cloud API (Meta) — required ---
    wa_phone_number_id: str
    wa_access_token: str
    wa_webhook_verify_token: str
    wa_app_secret: str

    # --- Core infra — required ---
    database_url: str
    redis_url: str

    # --- OpenAI — required (sole external AI vendor) ---
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o-mini"

    # --- Sarvam AI — cheap, Indic-native primary tier for structured Bengali
    # text (extraction, corrections, phrasing, captions) and for Bengali<->English
    # translation. Optional: if left blank, that tier is skipped and OpenAI
    # handles everything (functionally identical to the pre-Sarvam build). ---
    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_chat_model: str = "sarvam-30b"
    routine_confidence_floor: float = 0.80

    # --- Self-hosted, optional fallback tier (no third-party API) ---
    # Two independent knobs: a generic local chat model (Qwen etc. via Ollama),
    # and/or your own Q4-quantized sarvam-translate box (served OpenAI-compatible,
    # e.g. via vLLM) for zero-marginal-cost translation once you've bought/tuned it.
    use_local_models: bool = False
    ollama_base_url: str = "http://ollama:11434"
    ollama_llm_model: str = "qwen2.5:7b-instruct-q4_K_M"
    sarvam_local_base_url: str = ""  # e.g. http://localhost:8000/v1 (vLLM), blank = disabled

    # --- Self-hosted STT fallback (always available, no key needed) ---
    whisper_model_path: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # --- Object storage ---
    s3_bucket: str = "kotha-khata-assets"
    aws_region: str = "blr1"
    s3_endpoint_url: str = ""

    # --- Optional external data source ---
    data_gov_in_api_key: str = ""

    # --- Optional observability ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://langfuse:3000"

    debug: bool = False
    session_ttl_seconds: int = 1800
    max_messages_per_hour: int = 30
    max_text_message_chars: int = 2000

    # Ad poster text overlay — must be a TTF/OTF that covers Bengali glyphs
    # (Noto Sans Bengali recommended). If missing, poster generation degrades
    # gracefully to the plain processed photo + a separate caption message.
    bengali_font_path: str = "assets/fonts/NotoSansBengali-Bold.ttf"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
