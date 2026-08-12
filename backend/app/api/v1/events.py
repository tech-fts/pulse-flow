import json

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis

from app.core.redis import get_redis_client
from app.schemas.event import EventIngest, EventResponse
from app.services.rate_limiter import is_rate_limited
from app.services.stream import push_event, stream_name

router = APIRouter()


@router.post(
    "/events",
    response_model=EventResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_event(
    event: EventIngest,
    redis: Redis = Depends(get_redis_client),
) -> EventResponse:
    if await is_rate_limited(redis, f"ratelimit:{event.user_id}", limit=100):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    event_id = await push_event(
        redis,
        event.priority,
        user_id=event.user_id,
        channel=event.channel.value,
        payload=json.dumps(event.payload),
    )

    return EventResponse(event_id=event_id, queue=stream_name(event.priority))
