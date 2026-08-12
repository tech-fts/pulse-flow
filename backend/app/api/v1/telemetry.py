import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from app.core.redis import get_redis_client
from app.services.stream import queue_lengths

router = APIRouter()


async def telemetry_event_generator(redis: Redis):
    while True:
        lengths = await queue_lengths(redis)
        yield f"data: {json.dumps(lengths)}\n\n"
        await asyncio.sleep(1)


@router.get("/telemetry/stream")
async def stream_telemetry(redis: Redis = Depends(get_redis_client)):
    return StreamingResponse(
        telemetry_event_generator(redis),
        media_type="text/event-stream",
    )
