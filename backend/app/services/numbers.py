"""Gap-free document numbers (docs/05 §3): B/2026-27/000123, R/2026-27/000045."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NumberSequence

PREFIX = {"bill": "B", "receipt": "R"}


def format_number(kind: str, financial_year: str, value: int) -> str:
    return f"{PREFIX[kind]}/{financial_year}/{value:06d}"


async def reserve(
    session: AsyncSession, society_id: UUID, kind: str, financial_year: str, count: int
) -> int:
    """Lock the sequence row for the rest of the money transaction and take `count` numbers
    in one go, so numbers never have gaps or duplicates. Returns the first."""
    seq = await session.scalar(
        select(NumberSequence)
        .where(
            NumberSequence.society_id == society_id,
            NumberSequence.kind == kind,
            NumberSequence.financial_year == financial_year,
        )
        .with_for_update()
    )
    if seq is None:
        seq = NumberSequence(
            society_id=society_id, kind=kind, financial_year=financial_year, next_value=1
        )
        session.add(seq)
        await session.flush()
    first = seq.next_value
    seq.next_value = first + count
    return first
