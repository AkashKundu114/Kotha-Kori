from __future__ import annotations

import functools
import time

from langfuse import Langfuse

from shared.config.settings import get_settings

_client: Langfuse | None = None

def get_langfuse_client() -> Langfuse | None:
    global _client
    s = get_settings()
    if not s.langfuse_public_key:
        return None
    if _client is None:
        _client = Langfuse(
            public_key=s.langfuse_public_key,
            secret_key=s.langfuse_secret_key,
            host=s.langfuse_host,
        )
    return _client

def traced(name: str):
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            client = get_langfuse_client()
            start = time.monotonic()
            try:
                result = await fn(*args, **kwargs)
                return result
            finally:
                if client:
                    client.trace(
                        name=name,
                        metadata={"duration_seconds": round(time.monotonic() - start, 3)},
                    )
        return wrapper
    return decorator
