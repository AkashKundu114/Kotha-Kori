"""Fails loudly, in plain English, if a required .env value is missing —
so setup breaks at 'make setup' instead of at 3am inside a Celery worker."""
import os
import sys
from pathlib import Path

REQUIRED = [
    "WA_PHONE_NUMBER_ID",
    "WA_ACCESS_TOKEN",
    "WA_WEBHOOK_VERIFY_TOKEN",
    "WA_APP_SECRET",
    "OPENAI_API_KEY",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "DATABASE_URL",
    "REDIS_URL",
]

PLACEHOLDER_VALUES = {"", "changeme"}


def load_dotenv(path: str = ".env") -> dict:
    env = {}
    p = Path(path)
    if not p.exists():
        return env
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def main() -> int:
    env = {**load_dotenv(), **os.environ}
    missing = [k for k in REQUIRED if env.get(k, "").strip() in PLACEHOLDER_VALUES]

    if missing:
        print("Missing or placeholder values in .env — fill these in before `make dev`:\n")
        for k in missing:
            print(f"  - {k}")
        print("\nSee .env.example for where each one comes from.")
        return 1

    print("✅ All required .env values are set.")
    if not env.get("SARVAM_API_KEY", "").strip():
        print(
            "ℹ️  SARVAM_API_KEY is blank — the bot will run fine, but every "
            "message will go straight to OpenAI instead of the cheaper Sarvam "
            "tier. Recommended: get a key at sarvam.ai and set it."
        )
    if not os.path.exists(env.get("BENGALI_FONT_PATH", "assets/fonts/NotoSansBengali-Bold.ttf")):
        print(
            "ℹ️  Bengali font not found at BENGALI_FONT_PATH — ad posters will "
            "fall back to plain photo + separate caption messages. See "
            "assets/fonts/README.md to enable full poster generation."
        )
    if env.get("USE_LOCAL_MODELS", "false").lower() == "true":
        print("ℹ️  USE_LOCAL_MODELS=true — make sure you run:")
        print("    docker compose --profile local-models up -d ollama")
        print("    docker compose exec ollama ollama pull " + env.get("OLLAMA_LLM_MODEL", "qwen2.5:7b-instruct-q4_K_M"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
