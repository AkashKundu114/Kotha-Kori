import os
import sys
from pathlib import Path

REQUIRED = [
    "WA_PHONE_NUMBER_ID",
    "WA_ACCESS_TOKEN",
    "WA_WEBHOOK_VERIFY_TOKEN",
    "WA_APP_SECRET",
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

    sarvam_set = bool(env.get("SARVAM_API_KEY", "").strip())
    local_enabled = env.get("USE_LOCAL_MODELS", "false").lower() == "true"

    if not sarvam_set:
        print(
            "⚠️  SARVAM_API_KEY is blank — Sarvam is now the ONLY paid vendor "
            "(OpenAI has been removed entirely). Every agent will fail unless "
            "USE_LOCAL_MODELS=true and Ollama is actually reachable."
        )
    if not sarvam_set and not local_enabled:
        print(
            "❌ No paid tier (SARVAM_API_KEY) AND no free fallback "
            "(USE_LOCAL_MODELS=true) configured — every agent call will "
            "raise ModelUnavailableError. Set at least one before `make dev`."
        )
    if local_enabled:
        print("ℹ️  USE_LOCAL_MODELS=true — make sure you run:")
        print("    docker compose --profile local-models up -d ollama")
        print("    docker compose exec ollama ollama pull " + env.get("OLLAMA_LLM_MODEL", "qwen2.5:7b-instruct-q4_K_M"))
        print("    docker compose exec ollama ollama pull " + env.get("OLLAMA_VISION_MODEL", "qwen2-vl:7b-q4_K_M"))
    if not os.path.exists(env.get("BENGALI_FONT_PATH", "assets/fonts/NotoSansBengali-Bold.ttf")):
        print(
            "ℹ️  Bengali font not found at BENGALI_FONT_PATH — ad posters will "
            "fall back to plain photo + separate caption messages. See "
            "assets/fonts/README.md to enable full poster generation."
        )
    if not env.get("FLUX_API_KEY", "").strip():
        print(
            "ℹ️  FLUX_API_KEY is blank — poster generation will use the free, "
            "local Pillow composite only (always works, no code change needed)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
