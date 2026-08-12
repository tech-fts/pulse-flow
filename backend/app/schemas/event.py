from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventPriority(StrEnum):
    CRITICAL = "critical"
    STANDARD = "standard"
    BULK = "bulk"


class EventChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class EventIngest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=1, max_length=64)
    priority: EventPriority = EventPriority.STANDARD
    channel: EventChannel = EventChannel.SMS
    payload: dict[str, Any]

    @field_validator("payload")
    @classmethod
    def payload_must_fit_limit(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("payload must not be empty")
        return value


class EventResponse(BaseModel):
    event_id: str
    queue: str
    status: str = "accepted"
