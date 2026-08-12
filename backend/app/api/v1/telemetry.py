"""SSE telemetry — consumer-group lag, pending counts, and queue health."""
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)
router = APIRouter()

CONSUMER_GROUP = "dispatch-workers"


async def _collect_telemetry(redis: Redis) -> dict:
    """Collect per-stream health: backlog, pending, oldest pending age, DLQ count."""
    from app.services.stream import all_streams

    metrics: dict[str, dict] = {}

    for stream in all_streams():
        stream_data: dict[str, int | float | None] = {
            "length": await redis.xlen(stream),
            "pending": 0,
            "oldest_pending_age_sec": None,
        }

        try:
            pending_info = await redis.xpending(stream, CONSUMER_GROUP)
            stream_data["pending"] = pending_info.get("pending", 0)

            # Get oldest pending entry
            if pending_info.get("pending", 0) > 0:
                oldest = await redis.xpending_range(
                    stream, CONSUMER_GROUP, min="-", max="+", count=1
                )
                if oldest:
                    idle_ms = oldest[0].get("time_since_delivered", 0)
                    stream_data["oldest_pending_age_sec"] = round(idle_ms / 1000, 1)
        except Exception:
            pass  # Group may not exist yet

        metrics[stream] = stream_data

    # DLQ count
    try:
        metrics["stream:dead_letter"] = {
            "length": await redis.xlen("stream:dead_letter"),
            "pending": 0,
            "oldest_pending_age_sec": None,
        }
    except Exception:
        pass

    return metrics


async def telemetry_event_generator(request: Request, redis: Redis):
    try:
        while True:
            if await request.is_disconnected():
                break

            metrics = await _collect_telemetry(redis)
            yield f"data: {json.dumps(metrics)}\n\n"
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass


@router.get("/telemetry/stream")
async def stream_telemetry(
    request: Request,
    redis: Redis = Depends(get_redis_client),
):
    return StreamingResponse(
        telemetry_event_generator(request, redis),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )
