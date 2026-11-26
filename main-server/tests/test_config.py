"""Tests for Main Server settings and database URL normalization."""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings


@pytest.mark.parametrize(
    ("raw_url", "expected_url"),
    [
        (
            "postgres://user:pass@host:5432/db",
            "postgresql+asyncpg://user:pass@host:5432/db",
        ),
        (
            "postgresql://neondb_owner:secret@ep-demo.us-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://neondb_owner:secret@ep-demo.us-west-2.aws.neon.tech/neondb?ssl=require",
        ),
        (
            "postgresql://user:pass@ep-demo.neon.tech/neondb?sslmode=verify-full",
            "postgresql+asyncpg://user:pass@ep-demo.neon.tech/neondb?ssl=require",
        ),
        (
            "postgresql://user:pass@localhost:5432/db?sslmode=disable",
            "postgresql+asyncpg://user:pass@localhost:5432/db?ssl=disable",
        ),
        (
            "postgresql+asyncpg://user:pass@host/db?ssl=true",
            "postgresql+asyncpg://user:pass@host/db?ssl=require",
        ),
    ],
)
def test_database_url_normalization(raw_url: str, expected_url: str):
    settings = Settings(DATABASE_URL=raw_url)
    assert settings.database_url == expected_url


async def test_normalized_neon_url_accepted_by_asyncpg():
    neon_url = "postgresql://user:pass@127.0.0.1:59999/neondb?sslmode=require&channel_binding=require"
    settings = Settings(DATABASE_URL=neon_url)
    engine = create_async_engine(settings.database_url)
    try:
        with pytest.raises(OSError):
            async with engine.connect():
                pass
    finally:
        await engine.dispose()
