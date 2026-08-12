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
async def test_readyz(client: AsyncClient):
    response = await client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
