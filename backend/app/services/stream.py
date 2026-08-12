"""Redis Stream operations — canonical naming and transport-only publishing."""
from redis.asyncio import Redis

from app.core.config import settings
from app.db.models import OutboxMessage
from app.schemas.event import EventPriority


def stream_name(priority: EventPriority) -> str:
    return f"stream:{priority.value}"


def all_streams() -> list[str]:
    return [stream_name(p) for p in EventPriority]


async def publish_outbox_event(redis: Redis, message: OutboxMessage) -> str:
    """Publish a single outbox message to its target Redis Stream."""
    return await redis.xadd(
        message.stream_name,
        {
            "event_id": str(message.event_id),
            "delivery_id": str(message.delivery_id),
        },
        maxlen=settings.EVENT_STREAM_MAXLEN,
        approximate=True,
    )


async def queue_lengths(redis: Redis) -> dict[str, int]:
    """Return ``{stream_key: length}`` for every priority level."""
    return {s: await redis.xlen(s) for s in all_streams()}
