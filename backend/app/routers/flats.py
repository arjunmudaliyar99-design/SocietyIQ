"""Wings, flats and members (docs/02 §4). Manage: admin, treasurer, consultant. View: also
committee and auditor (docs/02 §2)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.deps import SessionDep, SocietyContext, require_role
from app.models import Member
from app.schemas.flats import (
    FlatDetailOut,
    FlatIn,
    FlatOut,
    FlatSummaryOut,
    FlatUpdate,
    MemberIn,
    MemberOut,
    MemberUpdate,
    WingIn,
    WingOut,
    WingUpdate,
)
from app.services import flats as service

router = APIRouter(prefix="/societies/{society_id}", tags=["flats"])

Viewer = Annotated[SocietyContext, Depends(require_role(*service.VIEW_ROLES))]
Manager = Annotated[SocietyContext, Depends(require_role(*service.MANAGE_ROLES))]


def _summary_out(s: service.FlatSummary) -> FlatSummaryOut:
    return FlatSummaryOut(
        **FlatOut.model_validate(s.flat).model_dump(),
        wing_name=s.wing_name,
        primary_member=s.primary_member,
        balance_paise=s.balance_paise,
    )


def _member_out(m: Member) -> MemberOut:
    out = MemberOut.model_validate(m)
    out.has_login = m.user_id is not None
    return out


@router.get("/wings")
async def list_wings(ctx: Viewer, session: SessionDep) -> list[WingOut]:
    return [WingOut.model_validate(w) for w in await service.list_wings(session, ctx.society_id)]


@router.post("/wings", status_code=status.HTTP_201_CREATED)
async def create_wing(body: WingIn, ctx: Manager, session: SessionDep) -> WingOut:
    wing = await service.create_wing(session, ctx.society_id, ctx.user, body.name, body.has_lift)
    return WingOut.model_validate(wing)


@router.patch("/wings/{wing_id}")
async def update_wing(
    wing_id: UUID, body: WingUpdate, ctx: Manager, session: SessionDep
) -> WingOut:
    wing = await service.update_wing(
        session, ctx.society_id, ctx.user, wing_id, body.model_dump(exclude_unset=True)
    )
    return WingOut.model_validate(wing)


@router.get("/flats")
async def list_flats(ctx: Viewer, session: SessionDep) -> list[FlatSummaryOut]:
    return [_summary_out(s) for s in await service.list_flats(session, ctx.society_id)]


@router.post("/flats", status_code=status.HTTP_201_CREATED)
async def create_flat(body: FlatIn, ctx: Manager, session: SessionDep) -> FlatOut:
    flat = await service.create_flat(session, ctx.society_id, ctx.user, body.model_dump())
    return FlatOut.model_validate(flat)


@router.get("/flats/{flat_id}")
async def get_flat(flat_id: UUID, ctx: Viewer, session: SessionDep) -> FlatDetailOut:
    detail = await service.flat_detail(session, ctx.society_id, flat_id)
    return FlatDetailOut(
        **_summary_out(detail.summary).model_dump(),
        members=[_member_out(m) for m in detail.members],
    )


@router.patch("/flats/{flat_id}")
async def update_flat(
    flat_id: UUID, body: FlatUpdate, ctx: Manager, session: SessionDep
) -> FlatOut:
    flat = await service.update_flat(
        session, ctx.society_id, ctx.user, flat_id, body.model_dump(exclude_unset=True)
    )
    return FlatOut.model_validate(flat)


@router.post("/flats/{flat_id}/members", status_code=status.HTTP_201_CREATED)
async def create_member(
    flat_id: UUID, body: MemberIn, ctx: Manager, session: SessionDep
) -> MemberOut:
    fields = body.model_dump()
    fields["email"] = str(body.email).lower() if body.email else None
    member = await service.create_member(session, ctx.society_id, ctx.user, flat_id, fields)
    return _member_out(member)


@router.patch("/flats/{flat_id}/members/{member_id}")
async def update_member(
    flat_id: UUID, member_id: UUID, body: MemberUpdate, ctx: Manager, session: SessionDep
) -> MemberOut:
    changes = body.model_dump(exclude_unset=True)
    if changes.get("email"):
        changes["email"] = str(changes["email"]).lower()
    member = await service.update_member(
        session, ctx.society_id, ctx.user, flat_id, member_id, changes
    )
    return _member_out(member)
