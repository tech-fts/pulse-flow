"""Redis Stream operations — single source of truth for stream naming and I/O."""
import uuid

from redis.asyncio import Redis

from app.schemas.event import EventPriority


def stream_name(priority: EventPriority) -> str:
    """Derive the Redis Stream key from an event priority — canonical naming."""
    return f"stream:{priority.value}"


def all_streams() -> list[str]:
    """All possible stream keys, derived from the EventPriority enum."""
    return [stream_name(p) for p in EventPriority]


def make_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:12]}"


async def push_event(
    redis: Redis,
    priority: EventPriority,
    /,
    *,
    user_id: str,
    channel: str,
    payload: str,
) -> str:
    """Push a serialized event payload onto the correct Redis Stream.

    Returns the generated ``event_id``.
    """
    event_id = make_event_id()
    key = stream_name(priority)
    await redis.xadd(
        key,
        {
            "event_id": event_id,
            "user_id": user_id,
            "channel": channel,
            "payload": payload,
        },
    )
    return event_id


async def queue_lengths(redis: Redis) -> dict[str, int]:
    """Return ``{stream_key: length}`` for every priority level."""
    return {s: await redis.xlen(s) for s in all_streams()}
