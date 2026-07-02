from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Create async engine for Neon Postgres.
# NullPool is recommended for serverless (Neon) to avoid stale pooled connections.
# NOTE: SSL is carried by the DATABASE_URL query string (e.g. ?sslmode=require for
# the psycopg driver, or ?ssl=require for asyncpg) — we do NOT pass sslmode via
# connect_args because that key is driver-specific and breaks asyncpg.
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.LOG_LEVEL == "DEBUG",
    poolclass=NullPool,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def ping_db() -> bool:
    """Health check for database connectivity."""
    if settings.MOCK_EXTERNAL_SERVICES:
        return True
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def close_db() -> None:
    """Close database engine on shutdown."""
    await engine.dispose()