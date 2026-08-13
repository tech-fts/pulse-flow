"""Unit tests for the LLM digest batcher (no infrastructure / API key needed)."""
from typing import cast

import pytest
from redis.asyncio import Redis

from app.workers.llm_batcher import (
    DailyDigest,
    DigestAgent,
    DigestItem,
    buffer_event,
    flush_user,
)


class FakeRedis:
    """Minimal in-memory stand-in for the Redis commands the batcher uses."""

    def __init__(self):
        self.lists: dict[str, list[str]] = {}
        self.sets: dict[str, set[str]] = {}
        self.expirations: dict[str, int] = {}

    async def rpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).append(value)

    async def sadd(self, key: str, member: str) -> None:
        self.sets.setdefault(key, set()).add(member)

    async def expire(self, key: str, ttl: int) -> None:
        self.expirations[key] = ttl

    async def lpop(self, key: str) -> str | None:
        lst = self.lists.get(key, [])
        return lst.pop(0) if lst else None

    async def smembers(self, key: str) -> set[str]:
        return set(self.sets.get(key, set()))

    async def srem(self, key: str, member: str) -> None:
        self.sets.get(key, set()).discard(member)


class FakeAgent:
    """Deterministic agent — never touches an LLM."""

    async def summarize(self, items: list[DigestItem]) -> DailyDigest:
        body = "; ".join(f"{i.category}: {i.title}" for i in items)
        return DailyDigest(subject=f"{len(items)} updates", body=body)


class TestDigestModels:
    def test_digest_item_roundtrip(self):
        item = DigestItem(category="security", title="New login", occurred_at="2026-08-13")
        assert DigestItem.model_validate_json(item.model_dump_json()) == item

    def test_daily_digest_requires_nonempty_fields(self):
        with pytest.raises(Exception):
            DailyDigest(subject="", body="")
        with pytest.raises(Exception):
            DailyDigest(subject="x", body="")


class TestBufferAndFlush:
    async def test_buffer_then_flush_produces_digest(self):
        redis = cast(Redis, FakeRedis())
        await buffer_event(redis, user_id="u1", category="security", title="Login")
        await buffer_event(redis, user_id="u1", category="transaction", title="Payment")

        # buffer_event uses the *current* day key; reconstruct it for the flush.
        from app.workers.llm_batcher import _day_key, _index_key

        day = _day_key()
        assert "u1" in await redis.smembers(_index_key(day))

        digest = await flush_user(redis, FakeAgent(), "u1", day)
        assert digest is not None
        assert digest.subject == "2 updates"
        assert "security: Login" in digest.body
        assert "transaction: Payment" in digest.body

        # buffer is drained and the user index is cleaned up.
        assert await redis.smembers(_index_key(day)) == set()

    async def test_flush_empty_buffer_returns_none(self):
        redis = cast(Redis, FakeRedis())
        result = await flush_user(redis, FakeAgent(), "ghost", "20260813")
        assert result is None


class TestDigestAgentFallback:
    async def test_summarize_falls_back_when_llm_unavailable(self):
        class BoomAgent(DigestAgent):
            async def _summarize_llm(self, items):
                raise RuntimeError("no api key")

        agent = BoomAgent(model="openai:gpt-4o-mini")
        digest = await agent.summarize(
            [DigestItem(category="security", title="Login", occurred_at="2026-08-13")]
        )
        assert digest.subject == "Your daily digest (1 updates)"
        assert "security: Login" in digest.body

    async def test_summarize_empty_raises(self):
        with pytest.raises(ValueError, match="zero"):
            await DigestAgent().summarize([])

    def test_fallback_is_deterministic(self):
        items = [DigestItem(category="a", title="t", occurred_at="2026-08-13")]
        first = DigestAgent._summarize_fallback(items)
        second = DigestAgent._summarize_fallback(items)
        assert first == second
