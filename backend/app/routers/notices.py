"""Notices (docs/02 §9). Admin drafts and publishes; committee members and consultants draft;
everyone in the society reads published notices meant for them (docs/02 §2)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app import ai
from app.deps import SessionDep, SocietyContext, require_role
from app.models import Notice
from app.schemas.notices import (
    AiDraftIn,
    AiTextOut,
    AiTranslateIn,
    NoticeDetailOut,
    NoticeIn,
    NoticeOptionsOut,
    NoticeOut,
    NoticeStatus,
    NoticeUpdate,
    TranslationOut,
)
from app.services import notices as service

router = APIRouter(prefix="/societies/{society_id}/notices", tags=["notices"])

Anyone = Annotated[SocietyContext, Depends(require_role())]
Drafter = Annotated[SocietyContext, Depends(require_role(*service.DRAFT_ROLES))]
Publisher = Annotated[SocietyContext, Depends(require_role(*service.PUBLISH_ROLES))]


def _out(n: Notice, read: set[UUID]) -> NoticeOut:
    return NoticeOut(
        id=n.id,
        title=n.title,
        body=n.body,
        language=n.language,
        audience=n.audience,
        audience_wing_id=n.audience_wing_id,
        status=n.status,
        ai_assisted=n.ai_assisted,
        published_at=n.published_at,
        created_at=n.created_at,
        updated_at=n.updated_at,
        is_read=n.id in read,
    )


async def _detail(session: SessionDep, ctx: SocietyContext, n: Notice) -> NoticeDetailOut:
    await session.refresh(n)
    manager = service.can_draft(ctx) or service.can_publish(ctx)
    out = NoticeDetailOut(
        **_out(n, await service.read_ids(session, ctx)).model_dump(),
        translations={
            lang: TranslationOut(
                title=t["title"], body=t["body"], reviewed=t.get("status") == "reviewed"
            )
            for lang, t in n.translations.items()
        },
        can_edit=service.can_draft(ctx) and n.status == "draft",
        can_publish=service.can_publish(ctx) and n.status == "draft",
    )
    if manager:
        c = await service.counts(session, ctx, n)
        out.read_count = c.read
        out.recipient_count = c.recipients
        out.emails_sent = c.sent
        out.emails_failed = c.failed
    return out


@router.get("")
async def list_notices(
    ctx: Anyone, session: SessionDep, status: Annotated[NoticeStatus | None, Query()] = None
) -> list[NoticeOut]:
    read = await service.read_ids(session, ctx)
    return [_out(n, read) for n in await service.list_notices(session, ctx, status)]


@router.get("/options")
async def options(ctx: Anyone) -> NoticeOptionsOut:
    return NoticeOptionsOut(ai_available=ai.ai_available())


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_notice(body: NoticeIn, ctx: Drafter, session: SessionDep) -> NoticeDetailOut:
    n = await service.create_notice(session, ctx, body.model_dump())
    return await _detail(session, ctx, n)


@router.post("/ai-draft")
async def ai_draft(body: AiDraftIn, ctx: Drafter) -> AiTextOut:
    text = await service.ai_draft(body.notes, body.language)
    return AiTextOut(title=text.title, body=text.body)


@router.get("/{notice_id}")
async def get_notice(notice_id: UUID, ctx: Anyone, session: SessionDep) -> NoticeDetailOut:
    return await _detail(session, ctx, await service.get_notice(session, ctx, notice_id))


@router.patch("/{notice_id}")
async def update_notice(
    notice_id: UUID, body: NoticeUpdate, ctx: Drafter, session: SessionDep
) -> NoticeDetailOut:
    changes = body.model_dump(exclude_unset=True)
    n = await service.update_notice(session, ctx, notice_id, changes)
    return await _detail(session, ctx, n)


@router.post("/{notice_id}/ai-translate")
async def ai_translate(
    notice_id: UUID, body: AiTranslateIn, ctx: Drafter, session: SessionDep
) -> NoticeDetailOut:
    n = await service.ai_translate(session, ctx, notice_id, list(body.languages))
    return await _detail(session, ctx, n)


@router.post("/{notice_id}/publish")
async def publish(notice_id: UUID, ctx: Publisher, session: SessionDep) -> NoticeDetailOut:
    result = await service.publish(session, ctx, notice_id)
    return await _detail(session, ctx, result.notice)


@router.post("/{notice_id}/archive")
async def archive(notice_id: UUID, ctx: Drafter, session: SessionDep) -> NoticeDetailOut:
    return await _detail(session, ctx, await service.archive(session, ctx, notice_id))


@router.post("/{notice_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(notice_id: UUID, ctx: Anyone, session: SessionDep) -> None:
    await service.mark_read(session, ctx, notice_id)
