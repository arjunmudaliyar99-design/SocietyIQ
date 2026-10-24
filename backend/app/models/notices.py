"""Notices, who read them, and every message sent (docs/05 §5, §8)."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedBy, Timestamps


class Notice(Timestamps, CreatedBy, Base):
    __tablename__ = "notices"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    title: Mapped[str]
    body: Mapped[str]
    language: Mapped[str] = mapped_column(server_default="en")
    # lang -> {title, body, status: 'draft' | 'reviewed'}
    translations: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    audience: Mapped[str] = mapped_column(server_default="all")
    audience_wing_id: Mapped[UUID | None]
    status: Mapped[str] = mapped_column(server_default="draft")
    ai_assisted: Mapped[bool] = mapped_column(server_default="false")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[UUID | None]


class NoticeRead(Base):
    __tablename__ = "notice_reads"

    notice_id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    society_id: Mapped[UUID]
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    channel: Mapped[str]
    template: Mapped[str]
    language: Mapped[str]
    to_member_id: Mapped[UUID | None]
    to_address_masked: Mapped[str]
    source_type: Mapped[str | None]
    source_id: Mapped[UUID | None]
    status: Mapped[str]
    provider_message_id: Mapped[str | None]
    error: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
