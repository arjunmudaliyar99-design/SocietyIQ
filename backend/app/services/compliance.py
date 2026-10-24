"""Vendors and the compliance tracker (docs/02 §13, docs/06 §9, docs/05 §6).

Status and the next due date come from app/calc/compliance. Every change writes an audit row
in the same transaction. Items are never deleted; they are turned off (is_active = false).
"""

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calc import compliance as calc
from app.errors import AppError, not_found
from app.models import ComplianceEvent, ComplianceItem, User, Vendor
from app.services import audit
from app.services.flats import snapshot

MANAGE_ROLES = ("admin", "treasurer", "committee", "consultant")
VIEW_ROLES = (*MANAGE_ROLES, "auditor")

VENDOR_FIELDS = ("name", "category", "phone_e164", "email", "gstin", "notes")
ITEM_FIELDS = (
    "item_type",
    "title",
    "vendor_id",
    "last_done_on",
    "next_due_on",
    "repeat_months",
    "contract_value_paise",
    "notes",
    "is_active",
)


def _clean(changes: dict[str, Any]) -> dict[str, Any]:
    return {k: (v.strip() or None if isinstance(v, str) else v) for k, v in changes.items()}


# --- vendors ---------------------------------------------------------------------------


async def list_vendors(session: AsyncSession, society_id: UUID) -> list[Vendor]:
    rows = await session.scalars(
        select(Vendor).where(Vendor.society_id == society_id).order_by(func.lower(Vendor.name))
    )
    return list(rows)


async def get_vendor(session: AsyncSession, society_id: UUID, vendor_id: UUID) -> Vendor:
    vendor = await session.get(Vendor, vendor_id)
    if vendor is None or vendor.society_id != society_id:
        raise not_found()
    return vendor


async def _vendor_name_taken(
    session: AsyncSession, society_id: UUID, name: str, except_id: UUID | None = None
) -> bool:
    query = select(Vendor.id).where(
        Vendor.society_id == society_id, func.lower(Vendor.name) == name.strip().lower()
    )
    if except_id:
        query = query.where(Vendor.id != except_id)
    return (await session.scalar(query)) is not None


async def create_vendor(
    session: AsyncSession, society_id: UUID, actor: User, fields: dict[str, Any]
) -> Vendor:
    fields = _clean(fields)
    if not fields.get("name"):
        raise AppError(422, "NAME_REQUIRED", "errors.generic")
    if await _vendor_name_taken(session, society_id, fields["name"]):
        raise AppError(409, "VENDOR_EXISTS", "errors.vendorExists")
    vendor = Vendor(society_id=society_id, created_by=actor.id, **fields)
    session.add(vendor)
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="vendor.create",
        entity_type="vendor",
        entity_id=vendor.id,
        after=snapshot(vendor, VENDOR_FIELDS),
    )
    return vendor


async def update_vendor(
    session: AsyncSession, society_id: UUID, actor: User, vendor_id: UUID, changes: dict[str, Any]
) -> Vendor:
    vendor = await get_vendor(session, society_id, vendor_id)
    changes = _clean(changes)
    if "name" in changes and not changes["name"]:
        raise AppError(422, "NAME_REQUIRED", "errors.generic")
    if changes.get("name") and await _vendor_name_taken(
        session, society_id, changes["name"], except_id=vendor.id
    ):
        raise AppError(409, "VENDOR_EXISTS", "errors.vendorExists")
    before = snapshot(vendor, VENDOR_FIELDS)
    for key, value in changes.items():
        setattr(vendor, key, value)
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="vendor.update",
        entity_type="vendor",
        entity_id=vendor.id,
        before=before,
        after=snapshot(vendor, VENDOR_FIELDS),
    )
    return vendor


# --- items ---------------------------------------------------------------------------


@dataclass
class ItemView:
    item: ComplianceItem
    vendor_name: str | None
    status: str
    days_left: int


def view(item: ComplianceItem, vendor_name: str | None, today: date) -> ItemView:
    # A finished one-off item is turned off when marked done; it is no longer due.
    state = calc.status(item.next_due_on, today) if item.is_active else "done"
    return ItemView(item, vendor_name, state, (item.next_due_on - today).days)


async def list_items(
    session: AsyncSession, society_id: UUID, today: date, *, active_only: bool = False
) -> list[ItemView]:
    query = (
        select(ComplianceItem, Vendor.name)
        .outerjoin(Vendor, Vendor.id == ComplianceItem.vendor_id)
        .where(ComplianceItem.society_id == society_id)
        .order_by(ComplianceItem.is_active.desc(), ComplianceItem.next_due_on, ComplianceItem.title)
    )
    if active_only:
        query = query.where(ComplianceItem.is_active)
    return [view(item, name, today) for item, name in await session.execute(query)]


async def get_item(session: AsyncSession, society_id: UUID, item_id: UUID) -> ComplianceItem:
    item = await session.get(ComplianceItem, item_id)
    if item is None or item.society_id != society_id:
        raise not_found()
    return item


async def item_view(
    session: AsyncSession, society_id: UUID, item: ComplianceItem, today: date
) -> ItemView:
    name = None
    if item.vendor_id:
        name = (await get_vendor(session, society_id, item.vendor_id)).name
    return view(item, name, today)


async def list_events(session: AsyncSession, item_id: UUID) -> list[ComplianceEvent]:
    rows = await session.scalars(
        select(ComplianceEvent)
        .where(ComplianceEvent.compliance_item_id == item_id)
        .order_by(ComplianceEvent.done_on.desc(), ComplianceEvent.created_at.desc())
    )
    return list(rows)


async def _check_vendor(session: AsyncSession, society_id: UUID, vendor_id: UUID | None) -> None:
    # Another society's vendor id gets the same answer as a made-up one.
    if vendor_id is not None:
        try:
            await get_vendor(session, society_id, vendor_id)
        except AppError:
            raise AppError(422, "VENDOR_NOT_FOUND", "errors.vendorNotFound") from None


async def create_item(
    session: AsyncSession, society_id: UUID, actor: User, fields: dict[str, Any]
) -> ComplianceItem:
    fields = _clean(fields)
    if not fields.get("title"):
        raise AppError(422, "TITLE_REQUIRED", "errors.generic")
    await _check_vendor(session, society_id, fields.get("vendor_id"))
    item = ComplianceItem(society_id=society_id, created_by=actor.id, **fields)
    session.add(item)
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="compliance_item.create",
        entity_type="compliance_item",
        entity_id=item.id,
        after=snapshot(item, ITEM_FIELDS),
    )
    return item


async def update_item(
    session: AsyncSession, society_id: UUID, actor: User, item_id: UUID, changes: dict[str, Any]
) -> ComplianceItem:
    item = await get_item(session, society_id, item_id)
    changes = _clean(changes)
    for required in ("item_type", "title", "next_due_on", "is_active"):
        if required in changes and changes[required] is None:
            raise AppError(422, "FIELD_REQUIRED", "errors.generic")
    if "vendor_id" in changes:
        await _check_vendor(session, society_id, changes["vendor_id"])
    before = snapshot(item, ITEM_FIELDS)
    for key, value in changes.items():
        setattr(item, key, value)
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="compliance_item.update",
        entity_type="compliance_item",
        entity_id=item.id,
        before=before,
        after=snapshot(item, ITEM_FIELDS),
    )
    return item


async def mark_done(
    session: AsyncSession,
    society_id: UUID,
    actor: User,
    item_id: UUID,
    done_on: date,
    notes: str | None,
    today: date,
) -> ComplianceItem:
    """docs/06 §9: next_due_on = done_on + repeat_months. A one-off item is turned off."""
    item = await get_item(session, society_id, item_id)
    if not item.is_active:
        raise AppError(409, "ITEM_NOT_ACTIVE", "errors.complianceNotActive")
    # A typo guard, not a rule: work cannot have been done on a day that has not come yet.
    if done_on > today:
        raise AppError(422, "DONE_IN_FUTURE", "errors.doneInFuture")
    before = snapshot(item, ITEM_FIELDS)
    session.add(
        ComplianceEvent(
            society_id=society_id,
            compliance_item_id=item.id,
            done_on=done_on,
            notes=(notes or "").strip() or None,
            recorded_by=actor.id,
        )
    )
    item.last_done_on = done_on
    next_due = calc.next_due_after(done_on, item.repeat_months)
    if next_due is None:
        item.is_active = False
    else:
        item.next_due_on = next_due
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="compliance_item.done",
        entity_type="compliance_item",
        entity_id=item.id,
        before=before,
        after=snapshot(item, ITEM_FIELDS),
    )
    return item
