from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # WhatsApp
    wa_phone_number_id: str
    wa_access_token: str
    wa_webhook_verify_token: str

    # Database
    database_url: str
    redis_url: str

    # Storage
    s3_bucket: str = "kotha-khata-assets"
    aws_region: str = "ap-south-1"

    # ── Voice cascade (tier 1: Sarvam, tier 2: Bhashini, tier 3: self-hosted) ──
    sarvam_api_key: str = ""
    sarvam_monthly_budget_inr: int = 15000  # cost-control valve; see voice_gateway
    bhashini_user_id: str = ""
    bhashini_api_key: str = ""
    whisper_model_path: str = "./models/bengali-large-v3"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"

    # ── LLM cascade ──────────────────────────────────────────────────
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://ollama:11434"
    ollama_llm_model: str = "kotha-khata-qwen:latest"
    ollama_vision_model: str = "kotha-khata-vision:latest"
    ollama_embedding_model: str = "nomic-embed-text"
    routine_confidence_floor: float = 0.80

    # ── Observability ────────────────────────────────────────────────
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://langfuse:3000"

    # App
    debug: bool = False
    session_ttl_seconds: int = 1800
    max_messages_per_hour: int = 30

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
