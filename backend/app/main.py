from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import events, telemetry
from app.core.config import settings
from app.core.database import dispose_database, engine
from app.core.redis import close_redis_pool, get_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis_pool()
    await dispose_database()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
)

app.include_router(events.router, prefix=settings.API_V1_STR)
app.include_router(telemetry.router, prefix=settings.API_V1_STR)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


async def _redis_ready() -> bool:
    try:
        redis = await get_redis()
        try:
            await redis.ping()
        finally:
            await redis.aclose()  # type: ignore[attr-defined]
        return True
    except Exception:
        return False


async def _database_ready() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@app.get("/readyz")
async def readyz(response: Response) -> dict[str, str | dict[str, bool]]:
    checks = {
        "redis": await _redis_ready(),
        "database": await _database_ready(),
    }
    ready = all(checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ready else "unavailable", "checks": checks}
