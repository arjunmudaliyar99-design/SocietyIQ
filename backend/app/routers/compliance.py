"""Compliance tracker and vendors (docs/02 §13). Roles per docs/02 §2: admin, treasurer,
committee and consultant manage; the auditor views."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.deps import SessionDep, SocietyContext, require_role
from app.schemas.compliance import (
    DoneIn,
    EventOut,
    ItemDetailOut,
    ItemIn,
    ItemOut,
    ItemUpdate,
    VendorIn,
    VendorOut,
    VendorUpdate,
)
from app.services import compliance as service
from app.timeutil import today_ist

router = APIRouter(prefix="/societies/{society_id}", tags=["compliance"])

Viewer = Annotated[SocietyContext, Depends(require_role(*service.VIEW_ROLES))]
Manager = Annotated[SocietyContext, Depends(require_role(*service.MANAGE_ROLES))]


def _out(v: service.ItemView) -> ItemOut:
    i = v.item
    return ItemOut(
        id=i.id,
        item_type=i.item_type,  # type: ignore[arg-type]
        title=i.title,
        vendor_id=i.vendor_id,
        vendor_name=v.vendor_name,
        last_done_on=i.last_done_on,
        next_due_on=i.next_due_on,
        repeat_months=i.repeat_months,
        contract_value_paise=i.contract_value_paise,
        notes=i.notes,
        is_active=i.is_active,
        status=v.status,  # type: ignore[arg-type]
        days_left=v.days_left,
    )


async def _detail(session: SessionDep, ctx: SocietyContext, item_id: UUID) -> ItemDetailOut:
    item = await service.get_item(session, ctx.society_id, item_id)
    v = await service.item_view(session, ctx.society_id, item, today_ist())
    events = [EventOut.model_validate(e) for e in await service.list_events(session, item.id)]
    return ItemDetailOut(**_out(v).model_dump(), events=events)


@router.get("/compliance/items")
async def list_items(ctx: Viewer, session: SessionDep) -> list[ItemOut]:
    return [_out(v) for v in await service.list_items(session, ctx.society_id, today_ist())]


@router.post("/compliance/items", status_code=status.HTTP_201_CREATED)
async def create_item(body: ItemIn, ctx: Manager, session: SessionDep) -> ItemDetailOut:
    item = await service.create_item(session, ctx.society_id, ctx.user, body.model_dump())
    return await _detail(session, ctx, item.id)


@router.get("/compliance/items/{item_id}")
async def get_item(item_id: UUID, ctx: Viewer, session: SessionDep) -> ItemDetailOut:
    return await _detail(session, ctx, item_id)


@router.patch("/compliance/items/{item_id}")
async def update_item(
    item_id: UUID, body: ItemUpdate, ctx: Manager, session: SessionDep
) -> ItemDetailOut:
    changes = body.model_dump(exclude_unset=True)
    await service.update_item(session, ctx.society_id, ctx.user, item_id, changes)
    return await _detail(session, ctx, item_id)


@router.post("/compliance/items/{item_id}/done")
async def mark_done(
    item_id: UUID, body: DoneIn, ctx: Manager, session: SessionDep
) -> ItemDetailOut:
    await service.mark_done(
        session, ctx.society_id, ctx.user, item_id, body.done_on, body.notes, today_ist()
    )
    return await _detail(session, ctx, item_id)


@router.get("/vendors")
async def list_vendors(ctx: Viewer, session: SessionDep) -> list[VendorOut]:
    rows = await service.list_vendors(session, ctx.society_id)
    return [VendorOut.model_validate(v) for v in rows]


@router.post("/vendors", status_code=status.HTTP_201_CREATED)
async def create_vendor(body: VendorIn, ctx: Manager, session: SessionDep) -> VendorOut:
    vendor = await service.create_vendor(session, ctx.society_id, ctx.user, body.model_dump())
    return VendorOut.model_validate(vendor)


@router.patch("/vendors/{vendor_id}")
async def update_vendor(
    vendor_id: UUID, body: VendorUpdate, ctx: Manager, session: SessionDep
) -> VendorOut:
    changes = body.model_dump(exclude_unset=True)
    vendor = await service.update_vendor(session, ctx.society_id, ctx.user, vendor_id, changes)
    return VendorOut.model_validate(vendor)
