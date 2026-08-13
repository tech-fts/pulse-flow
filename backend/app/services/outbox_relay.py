"""Outbox relay — claims unpublished outbox rows and publishes them to Redis Streams."""
import asyncio
import logging
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import SessionLocal
from app.core.redis import get_redis
from app.db.models import OutboxMessage
from app.services.stream import publish_outbox_event

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
POLL_INTERVAL = 1.0  # seconds


async def relay_pending() -> int:
    """Claim and publish a batch of unpublished outbox messages.

    Returns the number of messages published.
    """
    published = 0
    redis = await get_redis()

    async with SessionLocal() as session:
        async with session.begin():
            # Row-lock unpublished messages
            result = await session.execute(
                select(OutboxMessage)
                .where(OutboxMessage.published == False)  # noqa: E712
                .with_for_update(skip_locked=True)
                .limit(BATCH_SIZE)
            )
            messages = result.scalars().all()

            for msg in messages:
                try:
                    await publish_outbox_event(redis, msg)
                    msg.published = True
                    msg.published_at = datetime.now(timezone.utc)
                    published += 1
                except Exception:
                    logger.exception(
                        "Failed to publish outbox %s for event %s",
                        msg.id,
                        msg.event_id,
                    )
                    msg.attempt_count += 1

            # `session.begin()` commits on block exit; no explicit commit needed.

    return published


async def run_outbox_relay() -> None:
    """Continuously poll and publish pending outbox messages."""
    logger.info("Outbox relay started")
    while True:
        try:
            count = await relay_pending()
            if count > 0:
                logger.debug("Published %d outbox messages", count)
        except Exception:
            logger.exception("Outbox relay error")
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_outbox_relay())
