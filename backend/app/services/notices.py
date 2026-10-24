"""Notices and email (docs/02 §9, docs/04 §12, docs/05 §5).

Admin drafts and publishes; committee members and consultants draft (docs/02 §2). Residents
read published notices meant for them. Publishing is the only way a notice reaches anyone, and
only a person can press it: AI text never goes out on its own (docs/06 §12).
"""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import cache
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app import ai
from app.config import get_settings
from app.deps import SocietyContext
from app.errors import AppError, not_found
from app.models import (
    Flat,
    Member,
    Notice,
    NoticeRead,
    NotificationLog,
    Society,
    SocietyMembership,
    User,
    Wing,
)
from app.notify import Email, get_email_sender, mask_email
from app.services import audit

PUBLISH_ROLES = ("admin",)
DRAFT_ROLES = ("admin", "committee", "consultant")
LANGUAGES = ("en", "mr", "hi", "gu", "ta")

# Which members an audience reaches (docs/05 §2 member types).
AUDIENCE_MEMBER_TYPES = {
    "all": ("owner", "joint_owner", "tenant", "delegate"),
    "owners": ("owner", "joint_owner"),
    "tenants": ("tenant",),
    "wing": ("owner", "joint_owner", "tenant", "delegate"),
}
# Which app roles see an audience's notices in the resident app.
AUDIENCE_ROLES = {
    "owners": ("owner", "delegate"),
    "tenants": ("tenant",),
}

LABELS_FILE = Path(__file__).parent.parent / "i18n" / "email_labels.json"


@cache
def _labels() -> dict[str, dict[str, str]]:
    return json.loads(LABELS_FILE.read_text(encoding="utf-8"))


def can_draft(ctx: SocietyContext) -> bool:
    return bool(ctx.roles.intersection(DRAFT_ROLES))


def can_publish(ctx: SocietyContext) -> bool:
    return bool(ctx.roles.intersection(PUBLISH_ROLES))


def _now() -> datetime:
    return datetime.now(UTC)


def _snapshot(n: Notice) -> dict[str, Any]:
    return {
        "title": n.title,
        "language": n.language,
        "audience": n.audience,
        "audience_wing_id": str(n.audience_wing_id) if n.audience_wing_id else None,
        "status": n.status,
        "ai_assisted": n.ai_assisted,
        "translations": sorted(n.translations),
    }


async def _check_audience(
    session: AsyncSession, society_id: UUID, audience: str, wing_id: UUID | None
) -> UUID | None:
    if audience != "wing":
        return None
    if wing_id is None:
        raise AppError(422, "WING_REQUIRED", "errors.noticeChooseWing")
    wing = await session.get(Wing, wing_id)
    if wing is None or wing.society_id != society_id:
        raise not_found()
    return wing_id


# --- reading ---------------------------------------------------------------------------


@dataclass
class ResidentScope:
    roles: set[str]
    wing_ids: set[UUID]


async def _resident_scope(session: AsyncSession, ctx: SocietyContext) -> ResidentScope:
    rows = await session.execute(
        select(SocietyMembership.role, Flat.wing_id)
        .join(Flat, Flat.id == SocietyMembership.flat_id)
        .where(
            SocietyMembership.society_id == ctx.society_id,
            SocietyMembership.user_id == ctx.user.id,
            SocietyMembership.status == "active",
        )
    )
    roles: set[str] = set()
    wings: set[UUID] = set()
    for role, wing_id in rows:
        roles.add(role)
        wings.add(wing_id)
    return ResidentScope(roles=roles, wing_ids=wings)


async def list_notices(
    session: AsyncSession, ctx: SocietyContext, status: str | None = None
) -> list[Notice]:
    query = select(Notice).where(Notice.society_id == ctx.society_id)
    if can_draft(ctx) or can_publish(ctx):
        if status:
            query = query.where(Notice.status == status)
        order = func.coalesce(Notice.published_at, Notice.updated_at).desc()
        return list(await session.scalars(query.order_by(order)))

    # Everyone else reads published notices meant for them, newest first (docs/02 §11).
    query = query.where(Notice.status == "published")
    if not ctx.roles.intersection(("treasurer", "auditor")):
        scope = await _resident_scope(session, ctx)
        allowed = [Notice.audience == "all"]
        for audience, roles in AUDIENCE_ROLES.items():
            if scope.roles.intersection(roles):
                allowed.append(Notice.audience == audience)
        if scope.wing_ids:
            allowed.append(
                (Notice.audience == "wing") & Notice.audience_wing_id.in_(scope.wing_ids)
            )
        query = query.where(or_(*allowed))
    return list(await session.scalars(query.order_by(Notice.published_at.desc())))


async def get_notice(session: AsyncSession, ctx: SocietyContext, notice_id: UUID) -> Notice:
    n = await session.get(Notice, notice_id)
    if n is None or n.society_id != ctx.society_id:
        raise not_found()
    if not can_draft(ctx) and not can_publish(ctx):
        # Drafts and other audiences' notices look like they do not exist.
        if n.id not in {x.id for x in await list_notices(session, ctx)}:
            raise not_found()
    return n


async def read_ids(session: AsyncSession, ctx: SocietyContext) -> set[UUID]:
    rows = await session.scalars(
        select(NoticeRead.notice_id).where(
            NoticeRead.society_id == ctx.society_id, NoticeRead.user_id == ctx.user.id
        )
    )
    return set(rows)


async def mark_read(session: AsyncSession, ctx: SocietyContext, notice_id: UUID) -> None:
    n = await get_notice(session, ctx, notice_id)
    if n.status != "published":
        return
    await session.execute(
        insert(NoticeRead)
        .values(notice_id=n.id, user_id=ctx.user.id, society_id=ctx.society_id)
        .on_conflict_do_nothing()
    )


@dataclass
class Counts:
    read: int
    recipients: int
    sent: int
    failed: int


async def counts(session: AsyncSession, ctx: SocietyContext, n: Notice) -> Counts:
    read = await session.scalar(
        select(func.count()).where(
            NoticeRead.society_id == ctx.society_id, NoticeRead.notice_id == n.id
        )
    )
    log = dict(
        (
            await session.execute(
                select(NotificationLog.status, func.count())
                .where(
                    NotificationLog.society_id == ctx.society_id,
                    NotificationLog.source_type == "notice",
                    NotificationLog.source_id == n.id,
                )
                .group_by(NotificationLog.status)
            )
        ).all()
    )
    recipients = len(await _recipients(session, n))
    return Counts(
        read=read or 0,
        recipients=recipients,
        sent=log.get("sent", 0),
        failed=log.get("failed", 0),
    )


# --- drafting --------------------------------------------------------------------------


async def create_notice(
    session: AsyncSession, ctx: SocietyContext, fields: dict[str, Any]
) -> Notice:
    wing_id = await _check_audience(
        session, ctx.society_id, fields["audience"], fields.get("audience_wing_id")
    )
    n = Notice(
        society_id=ctx.society_id,
        title=fields["title"].strip(),
        body=fields["body"].strip(),
        language=fields["language"],
        audience=fields["audience"],
        audience_wing_id=wing_id,
        ai_assisted=fields.get("ai_assisted", False),
        status="draft",
        translations={},
        created_by=ctx.user.id,
    )
    session.add(n)
    await session.flush()
    await audit.record(
        session,
        society_id=ctx.society_id,
        actor_user_id=ctx.user.id,
        action="notice.create",
        entity_type="notice",
        entity_id=n.id,
        after=_snapshot(n),
    )
    return n


def _editable(n: Notice) -> None:
    if n.status != "draft":
        raise AppError(409, "NOTICE_NOT_DRAFT", "errors.noticeNotDraft")


async def update_notice(
    session: AsyncSession, ctx: SocietyContext, notice_id: UUID, changes: dict[str, Any]
) -> Notice:
    n = await get_notice(session, ctx, notice_id)
    _editable(n)
    before = _snapshot(n)
    for key in ("title", "body"):
        if changes.get(key) is not None:
            setattr(n, key, changes[key].strip())
    for key in ("language", "ai_assisted"):
        if changes.get(key) is not None:
            setattr(n, key, changes[key])
    if changes.get("audience") is not None or "audience_wing_id" in changes:
        audience = changes.get("audience") or n.audience
        wing = changes.get("audience_wing_id", n.audience_wing_id)
        n.audience_wing_id = await _check_audience(session, ctx.society_id, audience, wing)
        n.audience = audience
    if changes.get("translations") is not None:
        translations = dict(n.translations)
        for lang, value in changes["translations"].items():
            if value is None:
                translations.pop(lang, None)
            else:
                translations[lang] = {
                    "title": value["title"].strip(),
                    "body": value["body"].strip(),
                    "status": "reviewed" if value.get("reviewed", True) else "draft",
                }
        translations.pop(n.language, None)
        n.translations = translations
    n.updated_at = _now()
    await session.flush()
    await audit.record(
        session,
        society_id=ctx.society_id,
        actor_user_id=ctx.user.id,
        action="notice.update",
        entity_type="notice",
        entity_id=n.id,
        before=before,
        after=_snapshot(n),
    )
    return n


async def ai_draft(notes: str, language: str) -> ai.NoticeText:
    provider = ai.get_provider()
    raw = await provider.draft("notice_draft", {"notes": notes}, language)
    return ai.parse_notice_text(raw)


async def ai_translate(
    session: AsyncSession, ctx: SocietyContext, notice_id: UUID, languages: list[str]
) -> Notice:
    """Fills the chosen languages with unreviewed AI translations for a person to check."""
    n = await get_notice(session, ctx, notice_id)
    _editable(n)
    provider = ai.get_provider()
    translations = dict(n.translations)
    for lang in languages:
        if lang == n.language:
            continue
        raw = await provider.draft("notice_translate", {"title": n.title, "body": n.body}, lang)
        text = ai.parse_notice_text(raw)
        translations[lang] = {"title": text.title, "body": text.body, "status": "draft"}
    n.translations = translations
    n.ai_assisted = True
    n.updated_at = _now()
    await session.flush()
    return n


# --- publishing ------------------------------------------------------------------------


@dataclass
class Recipient:
    member_id: UUID
    email: str
    language: str


async def _recipients(session: AsyncSession, n: Notice) -> list[Recipient]:
    """One per current member with an email address in the audience (docs/07 M9). The same
    address listed twice (e.g. joint owners sharing one inbox) gets one email."""
    today = date.today()
    query = (
        select(Member.id, Member.email, User.preferred_language)
        .join(Flat, Flat.id == Member.flat_id)
        .outerjoin(User, User.id == Member.user_id)
        .where(
            Member.society_id == n.society_id,
            Member.email.is_not(None),
            Member.member_type.in_(AUDIENCE_MEMBER_TYPES[n.audience]),
            or_(Member.to_date.is_(None), Member.to_date >= today),
            Flat.is_active.is_(True),
        )
        .order_by(Member.email, Member.id)
    )
    if n.audience == "wing":
        query = query.where(Flat.wing_id == n.audience_wing_id)
    seen: set[str] = set()
    out: list[Recipient] = []
    for member_id, email, preferred in await session.execute(query):
        key = email.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(Recipient(member_id=member_id, email=key, language=preferred or n.language))
    return out


def _text_for(n: Notice, language: str) -> tuple[str, str, str]:
    """The reader's language when a reviewed translation exists; otherwise the original."""
    t = n.translations.get(language)
    if language != n.language and t and t.get("status") == "reviewed":
        return t["title"], t["body"], language
    return n.title, n.body, n.language


def build_email(n: Notice, society_name: str, to: str, language: str) -> tuple[Email, str]:
    title, body, lang = _text_for(n, language)
    labels = _labels()[lang]
    link = f"{get_settings().resident_pwa_url.rstrip('/')}/notices/{n.id}"
    text = "\n\n".join(
        [
            title,
            body,
            labels["noticeOpen"].format(link=link),
            "—",
            labels["noticeFooter"].format(society=society_name),
        ]
    )
    subject = labels["noticeSubject"].format(society=society_name, title=title)
    return Email(to=to, subject=subject, text=text), lang


@dataclass
class PublishResult:
    notice: Notice
    sent: int
    failed: int


async def publish(session: AsyncSession, ctx: SocietyContext, notice_id: UUID) -> PublishResult:
    n = await get_notice(session, ctx, notice_id)
    _editable(n)
    before = _snapshot(n)
    n.status = "published"
    n.published_at = _now()
    n.published_by = ctx.user.id
    n.updated_at = n.published_at
    society = await session.get(Society, ctx.society_id)
    society_name = society.name if society else ""

    # TODO(confirm): Q-082 — sending in the request is fine for one society's members with
    # the fake sender; a real provider may need a background job.
    sender = get_email_sender()
    sent = failed = 0
    for r in await _recipients(session, n):
        email, lang = build_email(n, society_name, r.email, r.language)
        try:
            result = await sender.send(email)
        except Exception as exc:  # noqa: BLE001 — one bad address must not stop the rest
            result_ok, message_id, error = False, None, type(exc).__name__
        else:
            result_ok, message_id, error = result.ok, result.provider_message_id, result.error
        session.add(
            NotificationLog(
                society_id=ctx.society_id,
                channel="email",
                template="notice",
                language=lang,
                to_member_id=r.member_id,
                to_address_masked=mask_email(r.email),
                source_type="notice",
                source_id=n.id,
                status="sent" if result_ok else "failed",
                provider_message_id=message_id,
                error=(error or None) and str(error)[:500],
            )
        )
        if result_ok:
            sent += 1
        else:
            failed += 1
    await session.flush()
    await audit.record(
        session,
        society_id=ctx.society_id,
        actor_user_id=ctx.user.id,
        action="notice.publish",
        entity_type="notice",
        entity_id=n.id,
        before=before,
        after={**_snapshot(n), "emails_sent": sent, "emails_failed": failed},
    )
    return PublishResult(notice=n, sent=sent, failed=failed)


async def archive(session: AsyncSession, ctx: SocietyContext, notice_id: UUID) -> Notice:
    n = await get_notice(session, ctx, notice_id)
    if n.status == "archived":
        return n
    # Drafters may drop a draft; taking down what residents already see is the admin's call.
    if n.status == "published" and not can_publish(ctx):
        raise AppError(403, "FORBIDDEN", "errors.notAllowed")
    before = _snapshot(n)
    n.status = "archived"
    n.updated_at = _now()
    await session.flush()
    await audit.record(
        session,
        society_id=ctx.society_id,
        actor_user_id=ctx.user.id,
        action="notice.archive",
        entity_type="notice",
        entity_id=n.id,
        before=before,
        after=_snapshot(n),
    )
    return n
