import asyncio
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from app.core.redis import get_redis_client

router = APIRouter()

async def telemetry_event_generator(redis: Redis):
    while True:
        critical_len = await redis.xlen("stream:critical")
        standard_len = await redis.xlen("stream:standard")
        bulk_len = await redis.xlen("stream:bulk")


        data = {
            "critical_queue": critical_len,
            "standard_queue": standard_len,
            "bulk_queue": bulk_len
        }

        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(1)  # Adjust the sleep time as needed

@router.get("/telemetry/stream")
async def stream_telemetry(redis: Redis = Depends(get_redis_client)):
    return StreamingResponse(telemetry_event_generator(redis), media_type="text/event-stream")