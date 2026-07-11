"""Dummy-but-valid required env vars so Settings() can be instantiated in
tests without a real .env file or real credentials. Individual tests still
monkeypatch specific values (and must call get_settings.cache_clear()
before/after, since it's lru_cache'd) when they need to control behavior."""
import os

_DEFAULTS = {
    "WA_PHONE_NUMBER_ID": "test-phone-id",
    "WA_ACCESS_TOKEN": "test-access-token",
    "WA_WEBHOOK_VERIFY_TOKEN": "test-verify-token",
    "WA_APP_SECRET": "test-app-secret",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
    "REDIS_URL": "redis://localhost:6379/0",
    "OPENAI_API_KEY": "test-openai-key",
}

for key, value in _DEFAULTS.items():
    os.environ.setdefault(key, value)
