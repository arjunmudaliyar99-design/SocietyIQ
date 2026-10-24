"""Complaints and their update history (docs/05 §5)."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps


class Complaint(Timestamps, Base):
    __tablename__ = "complaints"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    flat_id: Mapped[UUID | None]
    raised_by_user_id: Mapped[UUID | None]
    raised_on_behalf: Mapped[bool] = mapped_column(server_default="false")
    category: Mapped[str]
    location: Mapped[str]
    description: Mapped[str | None]
    status: Mapped[str] = mapped_column(server_default="open")
    assigned_to_text: Mapped[str | None]
    resident_feedback: Mapped[str | None]
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ComplaintUpdate(Base):
    __tablename__ = "complaint_updates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    complaint_id: Mapped[UUID]
    author_user_id: Mapped[UUID | None]
    message: Mapped[str]
    new_status: Mapped[str | None]
    visible_to_resident: Mapped[bool] = mapped_column(server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
