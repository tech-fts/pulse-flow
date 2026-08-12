from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventPriority(str, Enum):
    CRITICAL = "critical"
    STANDARD = "standard"
    BULK = "bulk"


class EventChannel(str, Enum):
    Email = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class EventIngest(BaseModel):
    user_id: str = Field(..., description="The ID of the user associated with the event")
    category: str = Field(..., description="The category of the event")
    priority: EventPriority = EventPriority.STANDARD
    channel: EventChannel = EventChannel.SMS
    payload: dict[str, Any] = Field(..., description="Event payload with relevant data")


class EventResponse(BaseModel):
    event_id: str
    queue: str
    status: str = Field(default="accepted", frozen=True)
