from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import events, telemetry

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
)

app.include_router(events.router, prefix=settings.API_V1_STR, tags=["Ingestion"])
app.include_router(telemetry.router, prefix=settings.API_V1_STR, tags=["Telemetry"])

@app.get("/healthz", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "DispatchOS Engine"}