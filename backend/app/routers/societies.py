"""Societies, invites, memberships (docs/02 §2-3). Every route under
/societies/{society_id} goes through require_role, which sets the RLS context."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.deps import CurrentUserDep, SessionDep, SocietyContext, require_role
from app.models import SocietyMembership
from app.schemas.societies import (
    AcceptInviteIn,
    CommitteeInviteIn,
    InviteIn,
    InviteOut,
    MembershipOut,
    SocietyCreatedOut,
    SocietyCreateIn,
    SocietyOut,
)
from app.services import societies as service

router = APIRouter(prefix="/societies", tags=["societies"])

AnyMember = Annotated[SocietyContext, Depends(require_role())]
# docs/02 §2: society settings, roles and invites are admin-only.
Admin = Annotated[SocietyContext, Depends(require_role("admin"))]


def _membership_out(m: SocietyMembership, you: UUID) -> MembershipOut:
    out = MembershipOut.model_validate(m)
    out.is_you = m.user_id == you
    return out


def _invite_out(created: service.CreatedInvite, you: UUID) -> InviteOut:
    return InviteOut(membership=_membership_out(created.membership, you), invite_link=created.link)


def _invite_input(body: InviteIn | CommitteeInviteIn) -> service.InviteInput:
    return service.InviteInput(
        role=body.role,
        name=body.name,
        email=str(body.email) if body.email else None,
        phone_e164=body.phone_e164,
        flat_id=body.flat_id if isinstance(body, InviteIn) else None,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_society(
    body: SocietyCreateIn, session: SessionDep, user: CurrentUserDep
) -> SocietyCreatedOut:
    # TODO(confirm): Q-032 — who may create a society (docs/02 §3: "done by us or the
    # admin"). For now any signed-in user can, and becomes its admin.
    fields = {**body.details.model_dump(), **body.billing.model_dump()}
    society, invites = await service.create_society(
        session, user, fields, [_invite_input(i) for i in body.invites]
    )
    return SocietyCreatedOut(
        society=SocietyOut.model_validate(society),
        invites=[_invite_out(i, user.id) for i in invites],
    )


@router.get("/{society_id}")
async def get_society(ctx: AnyMember, session: SessionDep) -> SocietyOut:
    return SocietyOut.model_validate(await service.get_society(session, ctx.society_id))


@router.get("/{society_id}/memberships")
async def list_memberships(ctx: Admin, session: SessionDep) -> list[MembershipOut]:
    rows = await service.list_memberships(session, ctx.society_id)
    return [_membership_out(m, ctx.user.id) for m in rows]


@router.post("/{society_id}/invites", status_code=status.HTTP_201_CREATED)
async def invite_member(body: InviteIn, ctx: Admin, session: SessionDep) -> InviteOut:
    created = await service.create_invite(session, ctx.society_id, ctx.user, _invite_input(body))
    return _invite_out(created, ctx.user.id)


# Not behind require_role: the person accepting is not a member yet. The token, scoped to
# this society, is the permission.
@router.post("/{society_id}/invites/accept")
async def accept_invite(
    society_id: UUID, body: AcceptInviteIn, session: SessionDep, user: CurrentUserDep
) -> MembershipOut:
    membership = await service.accept_invite(session, society_id, user, body.token)
    return _membership_out(membership, user.id)
