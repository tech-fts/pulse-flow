from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.event import EventIngest, EventResponse
from app.services import acceptance
from app.services.acceptance import DuplicateIdempotencyError

router = APIRouter()


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(
    event: EventIngest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    session: AsyncSession = Depends(get_db),
) -> EventResponse:
    # TODO: replace with real tenant extraction from auth token
    tenant_id = "default"

    try:
        accepted = await acceptance.accept(
            session=session,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            request=event,
        )
    except DuplicateIdempotencyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key reused with a different request body.",
        )

    stream_key = f"stream:{event.priority.value}"
    return EventResponse(event_id=str(accepted.id), queue=stream_key)
