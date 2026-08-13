"""LLM digest batcher — aggregates non-critical events into daily digests.

Non-critical (``standard``/``bulk``) events are buffered per user in Redis for
the current UTC day, then flushed through a PydanticAI agent into a single daily
digest notification.  This collapses N low-priority pings into one message,
eliminating notification fatigue.

The LLM call is isolated inside :class:`DigestAgent` with a deterministic
fallback, so the batching logic is fully testable offline and the worker
degrades gracefully when no model / API key is configured.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Protocol

from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.core.redis import get_redis
from app.schemas.event import EventPriority

logger = logging.getLogger(__name__)

# Only non-critical priorities are digested; critical events deliver immediately.
DIGEST_PRIORITIES = (EventPriority.STANDARD, EventPriority.BULK)

FLUSH_INTERVAL = 60  # seconds between digest flush passes
MAX_DIGEST_ITEMS = 50  # cap items drained per user per flush
DIGEST_TTL_SECONDS = 7 * 24 * 3600  # retain a day's buffer for one week

DEFAULT_MODEL = os.getenv("LLM_MODEL", "openai:gpt-4o-mini")


class DigestItem(BaseModel):
    """A single buffered, non-critical event awaiting digestion."""

    category: str
    title: str
    occurred_at: str


class DailyDigest(BaseModel):
    """The structured digest produced by the LLM agent (or fallback)."""

    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)


class DigestSummarizer(Protocol):
    """Structural interface for anything that turns buffered items into a digest."""

    async def summarize(self, items: list[DigestItem]) -> DailyDigest: ...


# ── Redis key helpers ──────────────────────────────────────────


def _day_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _buffer_key(user_id: str, day: str) -> str:
    return f"digest:{user_id}:{day}"


def _index_key(day: str) -> str:
    return f"digest:users:{day}"


async def buffer_event(
    redis: Redis,
    *,
    user_id: str,
    category: str,
    title: str,
) -> None:
    """Append a non-critical event to the user's daily digest buffer."""
    day = _day_key()
    item = DigestItem(
        category=category,
        title=title,
        occurred_at=datetime.now(timezone.utc).isoformat(),
    )
    buffer_key = _buffer_key(user_id, day)
    await redis.rpush(buffer_key, item.model_dump_json())
    await redis.sadd(_index_key(day), user_id)
    await redis.expire(buffer_key, DIGEST_TTL_SECONDS)
    await redis.expire(_index_key(day), DIGEST_TTL_SECONDS)


async def _drain(redis: Redis, key: str, limit: int) -> list[DigestItem]:
    """Atomically pop up to ``limit`` items from ``key`` (FIFO)."""
    items: list[DigestItem] = []
    for _ in range(limit):
        blob = await redis.lpop(key)
        if blob is None:
            break
        if isinstance(blob, list):
            continue  # defensively skip; a bare lpop never returns a list
        try:
            items.append(DigestItem.model_validate_json(blob))
        except Exception:
            logger.warning("Skipping malformed digest item in %s", key)
    return items


# ── LLM digest agent ───────────────────────────────────────────


class DigestAgent:
    """Wraps a PydanticAI agent; falls back to a templated digest offline."""

    def __init__(self, model: str | None = None) -> None:
        self._model = model or DEFAULT_MODEL
        self._agent = None  # lazily constructed on first LLM call

    async def summarize(self, items: list[DigestItem]) -> DailyDigest:
        if not items:
            raise ValueError("cannot summarize zero digest items")
        try:
            return await self._summarize_llm(items)
        except Exception as exc:  # noqa: BLE001 — degrade gracefully
            logger.warning("LLM digest unavailable (%s); using fallback", exc)
            return self._summarize_fallback(items)

    async def _summarize_llm(self, items: list[DigestItem]) -> DailyDigest:
        from pydantic_ai import Agent  # deferred import; keeps offline import cheap

        if self._agent is None:
            self._agent = Agent(
                self._model,
                system_prompt=(
                    "You write concise, friendly daily notification digests. "
                    "Summarize the user's activity in one short paragraph. "
                    "Never invent events that are not listed."
                ),
                output_type=DailyDigest,
            )
        prompt = (
            "Here is today's activity:\n"
            + "\n".join(f"- [{i.category}] {i.title}" for i in items)
            + "\n\nWrite a daily digest with a short subject and a 2-3 sentence body."
        )
        result = await self._agent.run(prompt)
        return result.output

    @staticmethod
    def _summarize_fallback(items: list[DigestItem]) -> DailyDigest:
        subject = f"Your daily digest ({len(items)} updates)"
        body = "Today: " + "; ".join(
            f"{item.category}: {item.title}" for item in items
        ) + "."
        return DailyDigest(subject=subject, body=body)


# ── Flush loop ─────────────────────────────────────────────────


async def flush_user(
    redis: Redis,
    agent: DigestSummarizer,
    user_id: str,
    day: str,
) -> DailyDigest | None:
    """Drain and digest one user's buffer.  Returns ``None`` if nothing buffered."""
    items = await _drain(redis, _buffer_key(user_id, day), MAX_DIGEST_ITEMS)
    if not items:
        return None
    digest = await agent.summarize(items)
    await redis.srem(_index_key(day), user_id)
    logger.info("Digest for %s: %s", user_id, digest.subject)
    return digest


async def flush_due_digests(redis: Redis, agent: DigestSummarizer) -> int:
    """Flush every user with buffered events for the current UTC day."""
    day = _day_key()
    user_ids = await redis.smembers(_index_key(day))
    flushed = 0
    for user_id in user_ids:
        uid = user_id.decode() if isinstance(user_id, bytes) else user_id
        if await flush_user(redis, agent, uid, day) is not None:
            flushed += 1
    return flushed


async def run_digest_batcher() -> None:
    """Continuously flush user digest buffers on a fixed interval."""
    redis = await get_redis()
    agent = DigestAgent()
    logger.info("Digest batcher started")
    while True:
        try:
            flushed = await flush_due_digests(redis, agent)
            if flushed:
                logger.info("Flushed %d user digests", flushed)
        except Exception:
            logger.exception("Digest batcher error")
        await asyncio.sleep(FLUSH_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_digest_batcher())
