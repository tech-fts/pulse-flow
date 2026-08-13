from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.schemas.event import EventIngest, EventPriority, EventResponse
from app.services import acceptance
from app.services.acceptance import DuplicateIdempotencyError
from app.services.rate_limiter import check_rate_limit
from app.workers.llm_batcher import buffer_event

router = APIRouter()


def _digest_title(event: EventIngest) -> str:
    payload_title = event.payload.get("title") or event.payload.get("message")
    return str(payload_title) if payload_title else event.category


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(
    event: EventIngest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
) -> EventResponse:
    # TODO: replace with real tenant extraction from auth token
    tenant_id = "default"

    limited = await check_rate_limit(
        redis, f"ratelimit:{tenant_id}", settings.RATE_LIMIT_PER_SECOND
    )
    if limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    try:
        if event.priority == EventPriority.CRITICAL:
            accepted = await acceptance.accept(
                session=session,
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
                request=event,
            )
            stream_key = f"stream:{event.priority.value}"
        else:
            accepted, created = await acceptance.accept_for_digest(
                session=session,
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
                request=event,
            )
            if created:
                await buffer_event(
                    redis,
                    user_id=event.user_id,
                    category=event.category,
                    title=_digest_title(event),
                )
            stream_key = "digest"
    except DuplicateIdempotencyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key reused with a different request body.",
        )

    return EventResponse(event_id=str(accepted.id), queue=stream_key)
