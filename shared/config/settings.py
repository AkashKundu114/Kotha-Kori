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

    # --- Sarvam AI — sole external AI vendor for chat, vision, and STT ---
    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_chat_model: str = "sarvam-30b"
    sarvam_advanced_model: str = "sarvam-105b"   # ads, negotiation, pricing phrasing
    sarvam_vision_model: str = "sarvam-vision"
    saaras_model: str = "saaras:v3"               # STT
    routine_confidence_floor: float = 0.80

    # --- Free, self-hosted fallback tier — NOT optional in spirit anymore.
    # With OpenAI removed, this is the ONLY thing keeping every agent alive
    # during a Sarvam outage or when SARVAM_API_KEY is unset entirely. The
    # toggle stays here because the GPU box is opt-in infra you provision
    # yourself, but running without it means a Sarvam outage goes fully
    # silent for every text/vision agent — see docs/architecture.md §8. ---
    use_local_models: bool = False
    ollama_base_url: str = "http://ollama:11434"
    ollama_llm_model: str = "qwen2.5:7b-instruct-q4_K_M"
    ollama_vision_model: str = "qwen2-vl:7b-q4_K_M"
    sarvam_local_base_url: str = ""  # your own vLLM-served sarvam-translate box, blank = disabled

    # --- Self-hosted STT fallback (always available, no key needed) ---
    whisper_model_path: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # --- Poster generation ---
    flux_api_key: str = ""          # optional paid upgrade tier; blank = Pillow-only (free, always works)
    flux_base_url: str = "https://api.bfl.ml"

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
