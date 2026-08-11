import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from app.services.rate_limiter import is_rate_limited
from app.core.redis import get_redis_client
from app.schemas.event import EventIngest, EventResponse

router = APIRouter()

@router.post("/events", response_model=EventResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(event: EventIngest, redis: Redis = Depends(get_redis_client)):
    # Rate limit per user
    if await is_rate_limited(redis, f"ratelimit:{event.user_id}", limit=100):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    stream_name = f"stream:{event.priority.value}"

    # push to designed Redis stream
    await redis.xadd(stream_name, 
                     {
                         "event_id": event_id,
                         "user_id": event.user_id,
                         "channel": event.channel.value,
                         "payload": json.dumps(event.payload)
                     })

    return EventResponse(event_id=event_id, queue=stream_name)


