"""Event acceptance — atomically commits Event, Delivery, OutboxMessage, IdempotencyKey."""
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import (
    Delivery,
    DeliveryStatus,
    Event,
    IdempotencyKey,
    OutboxMessage,
)
from app.schemas.event import EventIngest

IDEMPOTENCY_TTL_DAYS = 1


class DuplicateIdempotencyError(Exception):
    """Idempotency key reused with a different request body."""


async def accept(
    *,
    session: AsyncSession,
    tenant_id: str,
    idempotency_key: str,
    request: EventIngest,
) -> Event:
    """Accept an event atomically: insert Event, Delivery, OutboxMessage, IdempotencyKey.

    Raises ``DuplicateIdempotencyError`` if the idempotency key is reused
    with a different request body.
    """
    request_hash = _hash_request(request)

    # Check for existing idempotency key
    existing = await session.execute(
        select(IdempotencyKey).where(
            IdempotencyKey.tenant_id == tenant_id,
            IdempotencyKey.key == idempotency_key,
        )
    )
    row = existing.scalar_one_or_none()
    if row is not None:
        if row.request_hash != request_hash:
            raise DuplicateIdempotencyError(
                f"Idempotency key {idempotency_key} reused with different payload"
            )
        # Return the already-accepted event
        result = await session.execute(select(Event).where(Event.id == row.event_id))
        return result.scalar_one()

    # Insert Event
    event = Event(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=request.user_id,
        category=request.category,
        priority=request.priority.value,
        payload=request.payload,
    )
    session.add(event)

    # Insert Delivery
    delivery = Delivery(
        id=uuid.uuid4(),
        event_id=event.id,
        channel=request.channel.value,
        status=DeliveryStatus.PENDING,
    )
    session.add(delivery)

    # Insert OutboxMessage
    stream_key = f"stream:{request.priority.value}"
    outbox = OutboxMessage(
        id=uuid.uuid4(),
        event_id=event.id,
        delivery_id=delivery.id,
        stream_name=stream_key,
    )
    session.add(outbox)

    # Insert IdempotencyKey
    expiry = datetime.now(timezone.utc) + timedelta(days=IDEMPOTENCY_TTL_DAYS)
    key_row = IdempotencyKey(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        key=idempotency_key,
        request_hash=request_hash,
        event_id=event.id,
        expires_at=expiry,
    )
    session.add(key_row)

    await session.commit()
    return event


def _hash_request(request: EventIngest) -> str:
    raw = json.dumps(request.model_dump(), sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()
