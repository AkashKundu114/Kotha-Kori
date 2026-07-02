
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from shared.config.settings import get_settings

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        s = get_settings()
        _engine = create_async_engine(s.database_url, pool_size=10, max_overflow=20)
    return _engine

@asynccontextmanager
async def get_db_session():
    async with AsyncSession(get_engine()) as session:
        yield session
