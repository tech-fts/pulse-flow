"""Provider protocol and result types for notification delivery."""
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class DeliveryCommand:
    delivery_id: UUID
    event_id: UUID
    channel: str
    user_id: str
    payload: dict
    attempt: int


@dataclass(frozen=True)
class ProviderResult:
    provider_message_id: str


class RetryableProviderError(Exception):
    """Transient failure — the worker should retry with backoff."""


class PermanentProviderError(Exception):
    """Non-retryable failure — the delivery should go to DLQ."""


class NotificationProvider(Protocol):
    async def send(self, command: DeliveryCommand) -> ProviderResult: ...
