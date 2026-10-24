"""The flat's account (docs/05 §4). Append-only: never update or delete a row."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    flat_id: Mapped[UUID]
    entry_date: Mapped[date]
    entry_type: Mapped[str]
    # Signed: positive = flat owes more; negative = flat paid or was credited.
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    source_type: Mapped[str]
    source_id: Mapped[UUID | None]
    reverses_entry_id: Mapped[UUID | None]
    reason: Mapped[str | None]
    # Opening balances only: how many months they cover, for dues ageing.
    months_pending: Mapped[int | None]
    created_by: Mapped[UUID | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
