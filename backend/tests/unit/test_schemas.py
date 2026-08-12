"""Unit tests for request schemas."""
import pytest
from pydantic import ValidationError

from app.schemas.event import EventChannel, EventIngest, EventPriority, EventResponse


class TestEventIngest:
    def test_valid_minimal(self):
        e = EventIngest(user_id="u1", category="security", payload={"msg": "test"})
        assert e.priority == EventPriority.STANDARD
        assert e.channel == EventChannel.SMS

    def test_invalid_empty_user_id(self):
        with pytest.raises(ValidationError, match="user_id"):
            EventIngest(user_id="", category="x", payload={"k": "v"})

    def test_invalid_empty_payload(self):
        with pytest.raises(ValidationError, match="payload must not be empty"):
            EventIngest(user_id="u1", category="x", payload={})

    def test_forbids_extra_fields(self):
        with pytest.raises(ValidationError, match="extra"):
            EventIngest(
                user_id="u1",
                category="x",
                payload={"k": "v"},
                unknown_field=42,
            )


class TestEventResponse:
    def test_default_status(self):
        r = EventResponse(event_id="evt_1", queue="stream:standard")
        assert r.status == "accepted"
        d = r.model_dump()
        assert d["status"] == "accepted"
