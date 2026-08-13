"""Event acceptance — atomically commits Event, Delivery, OutboxMessage, IdempotencyKey.

Two paths share the same idempotent Event persistence:

* :func:`accept` — critical events, scheduled for immediate delivery (Delivery +
  OutboxMessage).
* :func:`accept_for_digest` — non-critical events, recorded for audit/idempotency
  but NOT delivered immediately; the caller buffers them into the daily digest.
"""
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
    """Accept a critical event and schedule immediate delivery.

    Raises ``DuplicateIdempotencyError`` if the idempotency key is reused
    with a different request body.
    """
    event, created = await _accept_event(session, tenant_id, idempotency_key, request)
    if not created:
        return event

    # Immediate delivery path — queue for a priority worker.
    stream_key = f"stream:{request.priority.value}"
    delivery = Delivery(
        id=uuid.uuid4(),
        event_id=event.id,
        channel=request.channel.value,
        status=DeliveryStatus.PENDING,
    )
    session.add(delivery)

    outbox = OutboxMessage(
        id=uuid.uuid4(),
        event_id=event.id,
        delivery_id=delivery.id,
        stream_name=stream_key,
    )
    session.add(outbox)

    await session.commit()
    return event


async def accept_for_digest(
    *,
    session: AsyncSession,
    tenant_id: str,
    idempotency_key: str,
    request: EventIngest,
) -> tuple[Event, bool]:
    """Accept a non-critical event for digest buffering.

    Persists the Event and IdempotencyKey for audit/dedup but does NOT create a
    Delivery or OutboxMessage — the caller buffers the event into the daily
    digest instead of delivering it immediately.

    Returns ``(event, created)`` where ``created`` is ``False`` when the
    idempotency key was replayed (the caller must not re-buffer in that case).
    """
    event, created = await _accept_event(session, tenant_id, idempotency_key, request)
    if created:
        await session.commit()
    return event, created


async def _accept_event(
    session: AsyncSession,
    tenant_id: str,
    idempotency_key: str,
    request: EventIngest,
) -> tuple[Event, bool]:
    """Idempotently persist the Event + IdempotencyKey. Returns ``(event, created)``."""
    request_hash = _hash_request(request)

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
        result = await session.execute(select(Event).where(Event.id == row.event_id))
        return result.scalar_one(), False

    event = Event(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=request.user_id,
        category=request.category,
        priority=request.priority.value,
        payload=request.payload,
    )
    session.add(event)

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

    return event, True


def _hash_request(request: EventIngest) -> str:
    raw = json.dumps(request.model_dump(), sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()
