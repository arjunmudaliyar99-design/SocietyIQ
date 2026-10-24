"""The flat ledger (docs/05 §4): append-only; balance = SUM(amount_paise)."""

from collections.abc import Iterable
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LedgerEntry


async def balances(session: AsyncSession, flat_ids: Iterable[UUID]) -> dict[UUID, int]:
    ids = list(flat_ids)
    if not ids:
        return {}
    rows = await session.execute(
        select(LedgerEntry.flat_id, func.coalesce(func.sum(LedgerEntry.amount_paise), 0))
        .where(LedgerEntry.flat_id.in_(ids))
        .group_by(LedgerEntry.flat_id)
    )
    found = {flat_id: int(total) for flat_id, total in rows}
    return {flat_id: found.get(flat_id, 0) for flat_id in ids}


async def add_opening_balance(
    session: AsyncSession,
    *,
    society_id: UUID,
    flat_id: UUID,
    amount_paise: int,
    entry_date: date,
    source_type: str,
    source_id: UUID | None,
    created_by: UUID | None,
) -> LedgerEntry:
    entry = LedgerEntry(
        society_id=society_id,
        flat_id=flat_id,
        entry_date=entry_date,
        entry_type="opening_balance",
        amount_paise=amount_paise,
        source_type=source_type,
        source_id=source_id,
        created_by=created_by,
    )
    session.add(entry)
    await session.flush()
    return entry
