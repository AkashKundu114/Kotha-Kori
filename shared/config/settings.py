from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    wa_phone_number_id: str
    wa_access_token: str
    wa_webhook_verify_token: str
    wa_app_secret: str
    wa_public_phone_number: str = ""
    wa_ledger_confirm_flow_id: str = ""
    public_base_url: str = "https://aisathi.app"

    database_url: str
    redis_url: str

    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_chat_model: str = "sarvam-30b"
    sarvam_advanced_model: str = "sarvam-105b"
    sarvam_vision_model: str = "sarvam-vision"
    saaras_model: str = "saaras:v3"
    routine_confidence_floor: float = 0.80

    use_local_models: bool = False
    ollama_base_url: str = "http://ollama:11434"
    ollama_llm_model: str = "qwen2.5:7b-instruct-q4_K_M"
    ollama_vision_model: str = "qwen2-vl:7b-q4_K_M"
    ollama_embedding_model: str = "nomic-embed-text"
    sarvam_local_base_url: str = ""

    whisper_model_path: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    flux_api_key: str = ""
    flux_base_url: str = "https://api.bfl.ml"

    s3_bucket: str = "kotha-khata-assets"
    aws_region: str = "blr1"
    s3_endpoint_url: str = ""

    data_gov_in_api_key: str = ""

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://langfuse:3000"

    debug: bool = False
    session_ttl_seconds: int = 1800
    max_messages_per_hour: int = 30
    max_text_message_chars: int = 2000

    bengali_font_path: str = "assets/fonts/NotoSansBengali-Bold.ttf"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
