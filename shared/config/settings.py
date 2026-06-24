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

    # ── Zero-Cost LLM Stack ──────────────────────────────────────
    ollama_base_url: str = "http://ollama:11434"
    # Fine-tuned Qwen2.5-7B served via Ollama
    ollama_llm_model: str = "kotha-khata-qwen:latest"
    # Fine-tuned Qwen2-VL-7B for vision
    ollama_vision_model: str = "kotha-khata-vision:latest"
    # nomic-embed-text (multilingual, Bengali support)
    ollama_embedding_model: str = "nomic-embed-text"

    # STT
    whisper_model_path: str = "./models/bengali-large-v3"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"

    # Optional external fallbacks
    bhashini_user_id: str = ""
    bhashini_api_key: str = ""

    # App
    debug: bool = False
    session_ttl_seconds: int = 1800
    max_messages_per_hour: int = 30

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
