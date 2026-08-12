import json
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from redis.asyncio import Redis

from app.core.redis import get_redis_client
from app.schemas.event import EventIngest, EventResponse
from app.services.rate_limiter import is_rate_limited

router = APIRouter()


@router.post(
    "/events",
    response_model=EventResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_event(
    event: EventIngest,
    idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    redis: Redis = Depends(get_redis_client),
) -> EventResponse:
    # 1. Idempotency Check (24h TTL)
    if idempotency_key:
        lock_key = f"idempotency:{idempotency_key}"
        is_new = await redis.set(lock_key, "1", nx=True, ex=86400)
        if not is_new:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate event: this idempotency key was already processed.",
            )

    # 2. Rate Limiting (token bucket, 100 req/s per user)
    if await is_rate_limited(redis, f"ratelimit:{event.user_id}", limit=100):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="User rate limit exceeded",
        )

    # 3. Push to priority Redis Stream with full record
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    stream_key = f"stream:{event.priority.value}"

    await redis.xadd(
        stream_key,
        {
            "event_id": event_id,
            "user_id": event.user_id,
            "category": event.category,
            "channel": event.channel.value,
            "payload": json.dumps(event.payload),
            "retry_count": "0",
        },
    )

    return EventResponse(event_id=event_id, queue=stream_key)
