"""Shared test fixtures — env vars MUST be set before any app import."""
import os

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

# Now safe to import app modules
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base


# ── Database fixtures ────────────────────────────────────────────


@pytest.fixture(scope="session")
def engine():
    """Session-scoped async engine."""
    url = os.environ["DATABASE_URL"]
    eng = create_async_engine(url, echo=False)
    yield eng


@pytest.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test session with automatic rollback."""
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as s:
        yield s
        await s.rollback()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── FastAPI app fixture ──────────────────────────────────────────


@pytest.fixture(scope="session")
def app():
    from app.main import app as _app
    return _app


@pytest.fixture
async def client(app):
    """Async httpx client wired to the FastAPI app (no network)."""
    from httpx import AsyncClient
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
