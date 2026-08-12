"""Fake notification provider — always succeeds, used for testing."""
import uuid

from app.integrations.providers.base import (
    DeliveryCommand,
    NotificationProvider,
    ProviderResult,
)


class FakeProvider:
    """A provider that always succeeds.  Used in tests and as a placeholder."""

    async def send(self, command: DeliveryCommand) -> ProviderResult:
        return ProviderResult(
            provider_message_id=f"fake-{uuid.uuid4().hex[:12]}"
        )
