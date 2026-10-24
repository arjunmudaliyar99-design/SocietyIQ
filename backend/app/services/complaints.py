"""Complaints and requests (docs/02 §8, docs/05 §5).

Two kinds of caller share these routes: the committee (manage every complaint) and residents
(raise and follow their own flat's complaints). Visibility is decided here, on top of RLS,
because RLS only separates societies, not flats.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import SocietyContext
from app.errors import AppError, not_found
from app.models import Attachment, Complaint, ComplaintUpdate, Flat, SocietyMembership
from app.services import audit
from app.services.societies import FLAT_ROLES
from app.storage import get_storage, store

# docs/02 §2: admin, treasurer and committee manage complaints; owners, tenants and
# delegates raise and see their own.
MANAGE_ROLES = ("admin", "treasurer", "committee")

# Forward through the flow of docs/02 §8, with a step back when work turns out unfinished.
TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"in_progress", "resolved", "closed"}),
    "in_progress": frozenset({"open", "resolved", "closed"}),
    "resolved": frozenset({"in_progress", "closed"}),
    "closed": frozenset({"in_progress"}),
}

# TODO(confirm): Q-080 — what the resident's "Fixed" / "Not fixed" does to the status.
# Placeholder: "Fixed" closes the complaint; "Not fixed" sends it back to In progress.
FEEDBACK_STATUS = {"fixed": "closed", "not_fixed": "in_progress"}

# Checked by content, not by name (docs/04 §7). Phone cameras give JPEG; galleries may
# also give PNG or WebP.
PHOTO_TYPES = (
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
)
MAX_PHOTOS = 3


def can_manage(ctx: SocietyContext) -> bool:
    return bool(ctx.roles.intersection(MANAGE_ROLES))


async def resident_flat_ids(session: AsyncSession, ctx: SocietyContext) -> set[UUID]:
    rows = await session.scalars(
        select(SocietyMembership.flat_id).where(
            SocietyMembership.society_id == ctx.society_id,
            SocietyMembership.user_id == ctx.user.id,
            SocietyMembership.status == "active",
            SocietyMembership.role.in_(FLAT_ROLES),
        )
    )
    return {f for f in rows if f is not None}


def _snapshot(c: Complaint) -> dict[str, Any]:
    return {
        "status": c.status,
        "assigned_to_text": c.assigned_to_text,
        "resident_feedback": c.resident_feedback,
    }


def _now() -> datetime:
    return datetime.now(UTC)


def _set_status(c: Complaint, status: str) -> None:
    if status not in TRANSITIONS[c.status]:
        raise AppError(409, "BAD_STATUS_CHANGE", "errors.complaintStatusChange")
    c.status = status
    now = _now()
    if status == "resolved":
        c.resolved_at = now
    elif status == "closed":
        c.closed_at = now
    else:
        # Reopened: the old resolution no longer stands, and new feedback is needed.
        c.resolved_at = None
        c.closed_at = None
        c.resident_feedback = None
    c.updated_at = now


async def list_complaints(
    session: AsyncSession, ctx: SocietyContext, status: str | None = None
) -> list[Complaint]:
    query = select(Complaint).where(Complaint.society_id == ctx.society_id)
    if not can_manage(ctx):
        flats = await resident_flat_ids(session, ctx)
        query = query.where(
            or_(Complaint.flat_id.in_(flats), Complaint.raised_by_user_id == ctx.user.id)
        )
    if status:
        query = query.where(Complaint.status == status)
    return list(await session.scalars(query.order_by(Complaint.created_at.desc())))


async def get_complaint(
    session: AsyncSession, ctx: SocietyContext, complaint_id: UUID
) -> Complaint:
    c = await session.get(Complaint, complaint_id)
    if c is None or c.society_id != ctx.society_id:
        raise not_found()
    if not can_manage(ctx):
        # Another flat's complaint looks the same as one that does not exist.
        mine = c.raised_by_user_id == ctx.user.id
        if not mine and c.flat_id not in await resident_flat_ids(session, ctx):
            raise not_found()
    return c


async def create_complaint(
    session: AsyncSession, ctx: SocietyContext, fields: dict[str, Any]
) -> Complaint:
    flat_id: UUID | None = fields.get("flat_id")
    manager = can_manage(ctx)
    if manager:
        if flat_id is not None:
            flat = await session.get(Flat, flat_id)
            if flat is None or flat.society_id != ctx.society_id:
                raise not_found()
    else:
        flats = await resident_flat_ids(session, ctx)
        if not flats:
            raise AppError(403, "FORBIDDEN", "errors.notAllowed")
        if flat_id is None:
            if len(flats) > 1:
                raise AppError(422, "FLAT_REQUIRED", "errors.complaintChooseFlat")
            flat_id = next(iter(flats))
        elif flat_id not in flats:
            raise not_found()
    if fields["location"] == "my_flat" and flat_id is None:
        raise AppError(422, "FLAT_REQUIRED", "errors.complaintChooseFlat")

    description = (fields.get("description") or "").strip() or None
    c = Complaint(
        id=uuid4(),
        society_id=ctx.society_id,
        flat_id=flat_id,
        raised_by_user_id=ctx.user.id,
        # A committee member raising for a flat is doing it for a resident without a phone.
        raised_on_behalf=manager and flat_id is not None,
        category=fields["category"],
        location=fields["location"],
        description=description,
        status="open",
    )
    session.add(c)
    await session.flush()
    await audit.record(
        session,
        society_id=ctx.society_id,
        actor_user_id=ctx.user.id,
        action="complaint.create",
        entity_type="complaint",
        entity_id=c.id,
        after={"category": c.category, "location": c.location, **_snapshot(c)},
    )
    return c


async def add_update(
    session: AsyncSession,
    ctx: SocietyContext,
    complaint_id: UUID,
    message: str,
    new_status: str | None,
    visible_to_resident: bool,
) -> Complaint:
    c = await get_complaint(session, ctx, complaint_id)
    before = _snapshot(c)
    if new_status == c.status:
        new_status = None
    if new_status:
        _set_status(c, new_status)
    else:
        c.updated_at = _now()
    session.add(
        ComplaintUpdate(
            society_id=ctx.society_id,
            complaint_id=c.id,
            author_user_id=ctx.user.id,
            message=message.strip(),
            new_status=new_status,
            visible_to_resident=visible_to_resident,
        )
    )
    await session.flush()
    if new_status:
        await audit.record(
            session,
            society_id=ctx.society_id,
            actor_user_id=ctx.user.id,
            action="complaint.status",
            entity_type="complaint",
            entity_id=c.id,
            before=before,
            after=_snapshot(c),
        )
    return c


async def assign(
    session: AsyncSession, ctx: SocietyContext, complaint_id: UUID, assigned_to: str | None
) -> Complaint:
    c = await get_complaint(session, ctx, complaint_id)
    before = _snapshot(c)
    c.assigned_to_text = (assigned_to or "").strip() or None
    c.updated_at = _now()
    await session.flush()
    await audit.record(
        session,
        society_id=ctx.society_id,
        actor_user_id=ctx.user.id,
        action="complaint.assign",
        entity_type="complaint",
        entity_id=c.id,
        before=before,
        after=_snapshot(c),
    )
    return c


async def give_feedback(
    session: AsyncSession, ctx: SocietyContext, complaint_id: UUID, feedback: str
) -> Complaint:
    c = await get_complaint(session, ctx, complaint_id)
    if c.status != "resolved":
        raise AppError(409, "NOT_RESOLVED", "errors.complaintNotResolved")
    before = _snapshot(c)
    _set_status(c, FEEDBACK_STATUS[feedback])
    c.resident_feedback = feedback
    session.add(
        ComplaintUpdate(
            society_id=ctx.society_id,
            complaint_id=c.id,
            author_user_id=ctx.user.id,
            # Stored as a key so each reader sees it in their own language.
            message=f"complaints.feedback.{feedback}",
            new_status=c.status,
        )
    )
    await session.flush()
    await audit.record(
        session,
        society_id=ctx.society_id,
        actor_user_id=ctx.user.id,
        action="complaint.feedback",
        entity_type="complaint",
        entity_id=c.id,
        before=before,
        after=_snapshot(c),
    )
    return c


async def list_updates(
    session: AsyncSession, ctx: SocietyContext, complaint: Complaint
) -> list[ComplaintUpdate]:
    query = select(ComplaintUpdate).where(
        ComplaintUpdate.society_id == ctx.society_id,
        ComplaintUpdate.complaint_id == complaint.id,
    )
    if not can_manage(ctx):
        query = query.where(ComplaintUpdate.visible_to_resident.is_(True))
    return list(await session.scalars(query.order_by(ComplaintUpdate.created_at)))


async def photo_ids(session: AsyncSession, ctx: SocietyContext, complaint: Complaint) -> list[UUID]:
    rows = await session.scalars(
        select(Attachment.id)
        .where(
            Attachment.society_id == ctx.society_id,
            Attachment.owner_type == "complaint",
            Attachment.owner_id == complaint.id,
        )
        .order_by(Attachment.created_at)
    )
    return list(rows)


def photo_type(data: bytes) -> tuple[str, str]:
    for magic, mime, ext in PHOTO_TYPES:
        if data.startswith(magic):
            return mime, ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    raise AppError(415, "NOT_A_PHOTO", "errors.notAPhoto")


async def add_photo(
    session: AsyncSession,
    ctx: SocietyContext,
    complaint_id: UUID,
    filename: str | None,
    data: bytes,
) -> Attachment:
    c = await get_complaint(session, ctx, complaint_id)
    if len(data) > get_settings().max_upload_bytes:
        raise AppError(413, "FILE_TOO_LARGE", "errors.fileTooLarge")
    mime, ext = photo_type(data)
    if len(await photo_ids(session, ctx, c)) >= MAX_PHOTOS:
        raise AppError(409, "TOO_MANY_PHOTOS", "errors.tooManyPhotos")
    stored = await store(ctx.society_id, "complaints", ext, data, mime)
    attachment = Attachment(
        society_id=ctx.society_id,
        owner_type="complaint",
        owner_id=c.id,
        storage_path=stored.path,
        mime=mime,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        original_filename=(filename or "")[:200] or None,
        uploaded_by=ctx.user.id,
    )
    session.add(attachment)
    await session.flush()
    return attachment


@dataclass
class Photo:
    data: bytes
    mime: str


async def get_photo(
    session: AsyncSession, ctx: SocietyContext, complaint_id: UUID, attachment_id: UUID
) -> Photo:
    c = await get_complaint(session, ctx, complaint_id)
    a = await session.get(Attachment, attachment_id)
    if a is None or a.society_id != ctx.society_id or a.owner_type != "complaint":
        raise not_found()
    if a.owner_id != c.id:
        raise not_found()
    return Photo(data=await get_storage().get(a.storage_path), mime=a.mime)
