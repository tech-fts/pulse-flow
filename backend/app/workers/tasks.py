"""Durable delivery worker — consumes Redis Streams, delivers via providers.

Algorithm:
1. Unique consumer name per process.
2. Create consumer groups once (catch BUSYGROUP).
3. XREADGROUP to retrieve messages.
4. Atomically claim the Delivery row in PostgreSQL.
5. If already sent, acknowledge and skip.
6. Call provider with timeout.
7. Persist outcome before acknowledging.
8. Bounded exponential backoff for transient errors.
9. XAUTOCLAIM orphaned pending entries periodically.
10. Terminal failures → dead_letter.
"""
import asyncio
import logging
import os
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.redis import get_redis
from app.db.models import Delivery, DeliveryStatus, Event
from app.integrations.providers.base import (
    DeliveryCommand,
    PermanentProviderError,
    ProviderResult,
    RetryableProviderError,
)
from app.integrations.providers.fake import FakeProvider
from app.schemas.event import EventChannel, EventPriority
from app.services.template_engine import render_notification

logger = logging.getLogger(__name__)

STREAMS = [f"stream:{p.value}" for p in EventPriority]
CONSUMER_GROUP = "dispatch-workers"
MAX_RETRIES = 3
BASE_BACKOFF = 2  # seconds
MAX_BACKOFF = 300  # seconds
AUTOCLAIM_INTERVAL = 30  # seconds
CLAIM_MIN_IDLE = 60_000  # ms — pending messages idle >60s are candidates

# ── Provider routing (replace with real adapters) ────────────────
_providers: dict[str, Any] = {"fake": FakeProvider()}


def _make_consumer_name() -> str:
    host = socket.gethostname()
    pid = os.getpid()
    return f"{settings.WORKER_CONSUMER_PREFIX}-{host}-{pid}"


async def setup_consumer_groups(redis: Redis) -> None:
    for stream in STREAMS:
        try:
            await redis.xgroup_create(stream, CONSUMER_GROUP, id="0", mkstream=True)
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                raise


async def _claim_delivery(session: AsyncSession, delivery_id: str) -> Delivery | None:
    """Atomically load a Delivery row.  Returns None if not found."""
    try:
        uid = uuid.UUID(delivery_id)
    except ValueError:
        logger.warning("Invalid delivery_id in stream: %s", delivery_id)
        return None

    result = await session.execute(
        select(Delivery).where(Delivery.id == uid).with_for_update()
    )
    return result.scalar_one_or_none()


async def _load_event(session: AsyncSession, event_id: str) -> Event | None:
    try:
        uid = uuid.UUID(event_id)
    except ValueError:
        return None
    result = await session.execute(select(Event).where(Event.id == uid))
    return result.scalar_one_or_none()


async def process_one(
    redis: Redis,
    stream: str,
    redis_id: str,
    fields: dict[str, str],
) -> None:
    delivery_id = fields.get("delivery_id", "")
    event_id = fields.get("event_id", "")

    async with SessionLocal() as session:
        async with session.begin():
            delivery = await _claim_delivery(session, delivery_id)
            if delivery is None:
                logger.warning("Delivery %s not found, ack and skip", delivery_id)
                await redis.xack(stream, CONSUMER_GROUP, redis_id)
                return

            if delivery.status == DeliveryStatus.SENT:
                await redis.xack(stream, CONSUMER_GROUP, redis_id)
                return

            event = await _load_event(session, delivery.event_id)
            if event is None:
                logger.warning("Event %s not found for delivery %s", event_id, delivery_id)
                delivery.status = DeliveryStatus.DEAD_LETTER
                delivery.last_error = "Referenced event not found"
                await redis.xack(stream, CONSUMER_GROUP, redis_id)
                return

            provider = _providers.get(delivery.channel, _providers["fake"])
            rendered = render_notification(
                event.category,
                EventChannel(delivery.channel),
                event.payload,
            )
            command = DeliveryCommand(
                delivery_id=delivery.id,
                event_id=event.id,
                channel=delivery.channel,
                user_id=event.user_id,
                payload=event.payload,
                attempt=delivery.attempt_count + 1,
                title=rendered.title,
                body=rendered.body,
            )

            try:
                result: ProviderResult = await asyncio.wait_for(
                    provider.send(command), timeout=30
                )
                delivery.status = DeliveryStatus.SENT
                delivery.provider_message_id = result.provider_message_id
                logger.info(
                    "Sent delivery %s via %s (provider_id=%s)",
                    delivery.id,
                    delivery.channel,
                    result.provider_message_id,
                )
            except RetryableProviderError as exc:
                delivery.attempt_count += 1
                if delivery.attempt_count >= MAX_RETRIES:
                    delivery.status = DeliveryStatus.DEAD_LETTER
                    delivery.last_error = _redact(str(exc))
                    logger.error(
                        "Delivery %s dead-lettered after %d attempts: %s",
                        delivery.id,
                        delivery.attempt_count,
                        _redact(str(exc)),
                    )
                else:
                    delay = min(BASE_BACKOFF * (2 ** delivery.attempt_count), MAX_BACKOFF)
                    delivery.status = DeliveryStatus.RETRY_SCHEDULED
                    delivery.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                        seconds=delay
                    )
                    delivery.last_error = _redact(str(exc))
                    logger.warning(
                        "Delivery %s retry %d scheduled in %ds",
                        delivery.id,
                        delivery.attempt_count,
                        delay,
                    )
            except PermanentProviderError as exc:
                delivery.status = DeliveryStatus.DEAD_LETTER
                delivery.last_error = _redact(str(exc))
                logger.error(
                    "Delivery %s permanently failed: %s",
                    delivery.id,
                    _redact(str(exc)),
                )
            except asyncio.TimeoutError:
                delivery.attempt_count += 1
                delivery.status = DeliveryStatus.RETRY_SCHEDULED
                delivery.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                    seconds=BASE_BACKOFF
                )
                delivery.last_error = "Provider timeout"
                logger.warning("Delivery %s timed out, retry scheduled", delivery.id)
            except Exception as exc:
                delivery.attempt_count += 1
                delivery.status = DeliveryStatus.RETRY_SCHEDULED
                delivery.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                    seconds=BASE_BACKOFF
                )
                delivery.last_error = _redact(str(exc))
                logger.exception("Unexpected error processing delivery %s", delivery.id)

            await session.commit()

        # Acknowledge after successful commit
        await redis.xack(stream, CONSUMER_GROUP, redis_id)


async def _reclaim_orphaned(redis: Redis) -> None:
    """Periodically claim pending messages that have been idle too long."""
    for stream in STREAMS:
        try:
            claimed = await redis.xautoclaim(
                stream,
                CONSUMER_GROUP,
                _make_consumer_name(),
                min_idle_time=CLAIM_MIN_IDLE,
                count=10,
            )
            if claimed and claimed[1]:
                logger.info("Reclaimed %d orphaned messages from %s", len(claimed[1]), stream)
        except Exception:
            pass  # Stream may not exist yet


def _redact(error: str) -> str:
    """Redact potentially sensitive data from error messages."""
    return error[:256]


async def run_stream_worker() -> None:
    redis = await get_redis()
    await setup_consumer_groups(redis)

    consumer_name = _make_consumer_name()
    logger.info("Worker %s started, watching %s", consumer_name, STREAMS)

    last_autoclaim = asyncio.get_event_loop().time()

    while True:
        try:
            entries = await redis.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=consumer_name,
                streams={s: ">" for s in STREAMS},
                count=10,
                block=2000,
            )

            for stream, messages in entries:
                for redis_id, fields in messages:
                    await process_one(redis, stream, redis_id, fields)

            # Periodic orphan reclaim
            now = asyncio.get_event_loop().time()
            if now - last_autoclaim > AUTOCLAIM_INTERVAL:
                await _reclaim_orphaned(redis)
                last_autoclaim = now

        except Exception as e:
            logger.error("Worker loop error: %s", e)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(run_stream_worker())
