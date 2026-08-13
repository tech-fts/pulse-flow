"""Unit tests for the event acceptance paths (no live DB required)."""
import uuid

from app.db.models import Event
from app.schemas.event import EventIngest
from app.services import acceptance


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value


class _KeyRow:
    def __init__(self, request_hash, event_id):
        self.request_hash = request_hash
        self.event_id = event_id


class FakeSession:
    """Fake AsyncSession tracking add()/commit() and scripted execute() results."""

    def __init__(self, existing_key=None, existing_event=None):
        self._key = existing_key
        self._event = existing_event
        self._calls = 0
        self.added = []
        self.committed = False

    async def execute(self, stmt):
        self._calls += 1
        if self._calls == 1:
            return _Result(self._key)
        return _Result(self._event)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True


def _request() -> EventIngest:
    return EventIngest(
        user_id="usr_1",
        category="security",
        priority="critical",
        channel="sms",
        payload={"title": "New login"},
    )


class TestAccept:
    async def test_accept_creates_full_delivery_path(self):
        session = FakeSession()
        event = await acceptance.accept(
            session=session, tenant_id="t", idempotency_key="k", request=_request()
        )
        assert isinstance(event, Event)
        names = [type(o).__name__ for o in session.added]
        assert names == ["Event", "IdempotencyKey", "Delivery", "OutboxMessage"]
        assert session.committed

    async def test_accept_replay_returns_existing_event_without_new_rows(self):
        request = _request()
        key = _KeyRow(acceptance._hash_request(request), uuid.uuid4())
        existing = Event(
            id=key.event_id,
            tenant_id="t",
            user_id="usr_1",
            category="security",
            priority="critical",
            payload={"title": "New login"},
        )
        session = FakeSession(existing_key=key, existing_event=existing)
        event = await acceptance.accept(
            session=session, tenant_id="t", idempotency_key="k", request=request
        )
        assert event is existing
        assert session.added == []
        assert not session.committed


class TestAcceptForDigest:
    async def test_skips_delivery_and_outbox(self):
        session = FakeSession()
        event, created = await acceptance.accept_for_digest(
            session=session, tenant_id="t", idempotency_key="k", request=_request()
        )
        assert created is True
        assert isinstance(event, Event)
        names = [type(o).__name__ for o in session.added]
        assert "Delivery" not in names
        assert "OutboxMessage" not in names
        assert "Event" in names and "IdempotencyKey" in names
        assert session.committed

    async def test_replay_returns_created_false(self):
        request = _request()
        key = _KeyRow(acceptance._hash_request(request), uuid.uuid4())
        existing = Event(
            id=key.event_id,
            tenant_id="t",
            user_id="usr_1",
            category="security",
            priority="standard",
            payload={"title": "New login"},
        )
        session = FakeSession(existing_key=key, existing_event=existing)
        event, created = await acceptance.accept_for_digest(
            session=session, tenant_id="t", idempotency_key="k", request=request
        )
        assert created is False
        assert event is existing
        assert session.added == []
        assert not session.committed
