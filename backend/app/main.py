from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import events, telemetry

app = FastAPI(title=settings.PROJECT_NAME)

# ── CORS: explicit origins, no wildcard + credentials ─────────────
ALLOWED_ORIGINS = ["http://localhost:3000", "https://yourdomain.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Idempotency-Key"],
)

# ── Payload size limiting (1 MB) ─────────────────────────────────
MAX_PAYLOAD_BYTES = 1024 * 1024


@app.middleware("http")
async def limit_payload_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_PAYLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload size exceeds 1 MB limit",
        )
    return await call_next(request)


# ── Routers ───────────────────────────────────────────────────────
app.include_router(events.router, prefix=settings.API_V1_STR, tags=["Ingestion"])
app.include_router(telemetry.router, prefix=settings.API_V1_STR, tags=["Telemetry"])


@app.get("/healthz", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "DispatchOS Engine"}
