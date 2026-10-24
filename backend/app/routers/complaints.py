"""Complaints and requests (docs/02 §8). Admin, treasurer and committee manage; owners,
tenants and delegates raise and follow their own flat's complaints (docs/02 §2)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import Response

from app.config import get_settings
from app.deps import SessionDep, SocietyContext, require_role
from app.errors import AppError
from app.models import Complaint
from app.schemas.complaints import (
    AssignIn,
    ComplaintDetailOut,
    ComplaintIn,
    ComplaintOut,
    ComplaintUpdateIn,
    ComplaintUpdateOut,
    FeedbackIn,
    Status,
)
from app.services import complaints as service
from app.services.billing import flat_labels
from app.services.societies import FLAT_ROLES

router = APIRouter(prefix="/societies/{society_id}/complaints", tags=["complaints"])

Anyone = Annotated[SocietyContext, Depends(require_role(*service.MANAGE_ROLES, *FLAT_ROLES))]
Manager = Annotated[SocietyContext, Depends(require_role(*service.MANAGE_ROLES))]
Resident = Annotated[SocietyContext, Depends(require_role(*FLAT_ROLES))]


def _out(c: Complaint, labels: dict[UUID, str]) -> ComplaintOut:
    out = ComplaintOut.model_validate(c)
    out.flat_label = labels.get(c.flat_id) if c.flat_id else None
    return out


async def _detail(session: SessionDep, ctx: SocietyContext, c: Complaint) -> ComplaintDetailOut:
    labels = await flat_labels(session, ctx.society_id)
    return ComplaintDetailOut(
        **_out(c, labels).model_dump(),
        updates=[
            ComplaintUpdateOut.model_validate(u)
            for u in await service.list_updates(session, ctx, c)
        ],
        photo_ids=await service.photo_ids(session, ctx, c),
        can_manage=service.can_manage(ctx),
    )


@router.get("")
async def list_complaints(
    ctx: Anyone, session: SessionDep, status: Annotated[Status | None, Query()] = None
) -> list[ComplaintOut]:
    labels = await flat_labels(session, ctx.society_id)
    return [_out(c, labels) for c in await service.list_complaints(session, ctx, status)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_complaint(
    body: ComplaintIn, ctx: Anyone, session: SessionDep
) -> ComplaintDetailOut:
    c = await service.create_complaint(session, ctx, body.model_dump())
    return await _detail(session, ctx, c)


@router.get("/{complaint_id}")
async def get_complaint(complaint_id: UUID, ctx: Anyone, session: SessionDep) -> ComplaintDetailOut:
    return await _detail(session, ctx, await service.get_complaint(session, ctx, complaint_id))


@router.post("/{complaint_id}/updates", status_code=status.HTTP_201_CREATED)
async def add_update(
    complaint_id: UUID, body: ComplaintUpdateIn, ctx: Manager, session: SessionDep
) -> ComplaintDetailOut:
    c = await service.add_update(
        session, ctx, complaint_id, body.message, body.new_status, body.visible_to_resident
    )
    return await _detail(session, ctx, c)


@router.patch("/{complaint_id}/assignee")
async def assign(
    complaint_id: UUID, body: AssignIn, ctx: Manager, session: SessionDep
) -> ComplaintDetailOut:
    c = await service.assign(session, ctx, complaint_id, body.assigned_to_text)
    return await _detail(session, ctx, c)


@router.post("/{complaint_id}/feedback")
async def give_feedback(
    complaint_id: UUID, body: FeedbackIn, ctx: Resident, session: SessionDep
) -> ComplaintDetailOut:
    c = await service.give_feedback(session, ctx, complaint_id, body.feedback)
    return await _detail(session, ctx, c)


@router.post("/{complaint_id}/photos", status_code=status.HTTP_201_CREATED)
async def add_photo(
    complaint_id: UUID,
    file: Annotated[UploadFile, File()],
    ctx: Anyone,
    session: SessionDep,
) -> ComplaintDetailOut:
    limit = get_settings().max_upload_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise AppError(413, "FILE_TOO_LARGE", "errors.fileTooLarge")
    await service.add_photo(session, ctx, complaint_id, file.filename, data)
    return await _detail(session, ctx, await service.get_complaint(session, ctx, complaint_id))


@router.get("/{complaint_id}/photos/{attachment_id}", response_class=Response)
async def get_photo(
    complaint_id: UUID, attachment_id: UUID, ctx: Anyone, session: SessionDep
) -> Response:
    photo = await service.get_photo(session, ctx, complaint_id, attachment_id)
    return Response(
        content=photo.data,
        media_type=photo.mime,
        headers={"Cache-Control": "private, max-age=3600"},
    )
