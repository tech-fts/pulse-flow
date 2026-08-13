"""Unit tests for the event acceptance paths (no live DB required)."""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import Event, IdempotencyKey
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


def _integrity_error() -> IntegrityError:
    return IntegrityError(
        "INSERT INTO idempotency_keys ...",
        {},
        Exception(
            'duplicate key value violates unique constraint "uq_idempotency_tenant_key"'
        ),
    )


class FakeSession:
    """Scripted fake AsyncSession.

    ``results`` is a queue of values returned by successive ``execute()`` calls
    (each wrapped in ``_Result``).  ``commit_error``, when set, makes the first
    ``commit()`` raise that error (then clears).
    """

    def __init__(self, results=None, commit_error=None):
        self._results = list(results) if results else []
        self._commit_error = commit_error
        self.added = []
        self.committed = False
        self.rolled_back = False

    async def execute(self, stmt):
        value = self._results.pop(0) if self._results else None
        return _Result(value)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        if self._commit_error is not None:
            err, self._commit_error = self._commit_error, None
            raise err
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


def _request() -> EventIngest:
    return EventIngest(
        user_id="usr_1",
        category="security",
        priority="critical",
        channel="sms",
        payload={"title": "New login"},
    )


def _event(event_id, priority="critical") -> Event:
    return Event(
        id=event_id,
        tenant_id="t",
        user_id="usr_1",
        category="security",
        priority=priority,
        payload={"title": "New login"},
    )


class TestModel:
    def test_idempotency_has_unique_tenant_key_constraint(self):
        names = [c.name for c in IdempotencyKey.__table__.constraints]
        assert "uq_idempotency_tenant_key" in names


class TestAccept:
    async def test_accept_creates_full_delivery_path(self):
        session = FakeSession(results=[None])
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
        existing = _event(key.event_id)
        session = FakeSession(results=[key, existing])
        event = await acceptance.accept(
            session=session, tenant_id="t", idempotency_key="k", request=request
        )
        assert event is existing
        assert session.added == []
        assert not session.committed

    async def test_accept_recovers_from_idempotency_race(self):
        request = _request()
        winner_id = uuid.uuid4()
        winner = _event(winner_id)
        winner_key = _KeyRow(acceptance._hash_request(request), winner_id)
        session = FakeSession(
            results=[None, winner_key, winner], commit_error=_integrity_error()
        )
        event = await acceptance.accept(
            session=session, tenant_id="t", idempotency_key="k", request=request
        )
        assert event is winner
        assert session.rolled_back
        assert not session.committed

    async def test_race_with_different_payload_raises(self):
        request = _request()
        winner_key = _KeyRow("some_other_hash", uuid.uuid4())
        session = FakeSession(
            results=[None, winner_key], commit_error=_integrity_error()
        )
        with pytest.raises(acceptance.DuplicateIdempotencyError):
            await acceptance.accept(
                session=session, tenant_id="t", idempotency_key="k", request=request
            )


class TestAcceptForDigest:
    async def test_skips_delivery_and_outbox(self):
        session = FakeSession(results=[None])
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
        existing = _event(key.event_id, priority="standard")
        session = FakeSession(results=[key, existing])
        event, created = await acceptance.accept_for_digest(
            session=session, tenant_id="t", idempotency_key="k", request=request
        )
        assert created is False
        assert event is existing
        assert session.added == []
        assert not session.committed

    async def test_recovers_from_idempotency_race_returns_created_false(self):
        request = _request()
        winner_id = uuid.uuid4()
        winner = _event(winner_id, priority="standard")
        winner_key = _KeyRow(acceptance._hash_request(request), winner_id)
        session = FakeSession(
            results=[None, winner_key, winner], commit_error=_integrity_error()
        )
        event, created = await acceptance.accept_for_digest(
            session=session, tenant_id="t", idempotency_key="k", request=request
        )
        assert created is False
        assert event is winner
        assert session.rolled_back
