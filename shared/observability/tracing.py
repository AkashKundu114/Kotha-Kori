from __future__ import annotations

import functools
import time

from shared.config.settings import get_settings

_client = None


def get_langfuse_client():
    global _client
    s = get_settings()
    if not s.langfuse_public_key:
        return None
    if _client is None:
        try:
            from langfuse import Langfuse

            _client = Langfuse(
                public_key=s.langfuse_public_key,
                secret_key=s.langfuse_secret_key,
                host=s.langfuse_host,
            )
        except Exception:
            return None
    return _client


def traced(name: str):
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            client = get_langfuse_client()
            start = time.monotonic()
            try:
                return await fn(*args, **kwargs)
            finally:
                if client:
                    try:
                        client.trace(
                            name=name,
                            metadata={"duration_seconds": round(time.monotonic() - start, 3)},
                        )
                    except Exception:
                        pass

        return wrapper

    return decorator
