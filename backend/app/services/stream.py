"""Redis Stream operations — single source of truth for stream naming and I/O."""
import json
import uuid
from typing import Any

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
    category: str,
    channel: str,
    payload: dict[str, Any],
    idempotency_key: str | None = None,
) -> str:
    """Push a complete event record onto the correct Redis Stream.

    Includes idempotency guard (24h TTL) and ``retry_count: "0"`` for
    the consumer-group retry loop.

    Returns the generated ``event_id``.
    """
    if idempotency_key:
        is_new = await redis.set(
            f"idempotency:{idempotency_key}", "1", nx=True, ex=86400,
        )
        if not is_new:
            raise ValueError(f"Duplicate idempotency key: {idempotency_key}")

    event_id = make_event_id()
    key = stream_name(priority)
    await redis.xadd(
        key,
        {
            "event_id": event_id,
            "user_id": user_id,
            "category": category,
            "channel": channel,
            "payload": json.dumps(payload),
            "retry_count": "0",
        },
    )
    return event_id


async def queue_lengths(redis: Redis) -> dict[str, int]:
    """Return ``{stream_key: length}`` for every priority level."""
    return {s: await redis.xlen(s) for s in all_streams()}
