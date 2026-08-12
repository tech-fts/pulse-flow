import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_ingest_event_success():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        payload = {
            "user_id": "usr_test123",
            "category": "security",
            "priority": "critical",
            "channel": "sms",
            "payload": {"title": "Verification Code", "code": "123456"},
        }
        response = await ac.post("/api/v1/events", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "event_id" in data
        assert data["queue"] == "stream:critical"


@pytest.mark.asyncio
async def test_idempotency_enforcement():
    headers = {"X-Idempotency-Key": "unique-request-key-001"}
    payload = {
        "user_id": "usr_test123",
        "category": "billing",
        "priority": "standard",
        "channel": "email",
        "payload": {"amount": 50},
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # First request succeeds
        r1 = await ac.post("/api/v1/events", json=payload, headers=headers)
        assert r1.status_code == 202

        # Second request with duplicate key gets blocked
        r2 = await ac.post("/api/v1/events", json=payload, headers=headers)
        assert r2.status_code == 409
