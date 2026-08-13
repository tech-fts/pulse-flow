"""Integration tests for event acceptance flow."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_accept_event_requires_idempotency_key(client: AsyncClient):
    payload = {
        "user_id": "usr_test123",
        "category": "security",
        "priority": "critical",
        "channel": "sms",
        "payload": {"title": "Test"},
    }
    response = await client.post("/api/v1/events", json=payload)
    # Missing Idempotency-Key header → 422 validation error
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_payload_rejected(client: AsyncClient):
    headers = {"Idempotency-Key": "key-001"}
    payload = {
        "user_id": "usr_1",
        "category": "sec",
        "payload": {},
    }
    response = await client.post(
        "/api/v1/events", json=payload, headers=headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_extra_fields_rejected(client: AsyncClient):
    headers = {"Idempotency-Key": "key-002"}
    payload = {
        "user_id": "usr_1",
        "category": "sec",
        "payload": {"k": "v"},
        "bad_field": "nope",
    }
    response = await client.post(
        "/api/v1/events", json=payload, headers=headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_healthz(client: AsyncClient):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readyz(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    async def _ok() -> bool:
        return True

    monkeypatch.setattr("app.main._redis_ready", _ok)
    monkeypatch.setattr("app.main._database_ready", _ok)
    response = await client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_readyz_unavailable_when_redis_down(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    async def _redis_down() -> bool:
        return False

    async def _db_ok() -> bool:
        return True

    monkeypatch.setattr("app.main._redis_ready", _redis_down)
    monkeypatch.setattr("app.main._database_ready", _db_ok)
    response = await client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


@pytest.mark.asyncio
async def test_rate_limited_returns_429(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    async def _limited(redis, key, limit):
        return True

    monkeypatch.setattr("app.api.v1.events.check_rate_limit", _limited)
    headers = {"Idempotency-Key": "key-rate-001"}
    payload = {
        "user_id": "usr_1",
        "category": "security",
        "priority": "critical",
        "channel": "sms",
        "payload": {"title": "Test"},
    }
    response = await client.post("/api/v1/events", json=payload, headers=headers)
    assert response.status_code == 429
