"""System tables (docs/05 §3 legal_parameters, §8)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Numeric, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    society_id: Mapped[UUID | None]
    actor_user_id: Mapped[UUID | None]
    action: Mapped[str]
    entity_type: Mapped[str]
    entity_id: Mapped[UUID | None]
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reason: Mapped[str | None]
    ip: Mapped[str | None] = mapped_column(INET)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LegalParameter(Base):
    __tablename__ = "legal_parameters"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str]
    value: Mapped[Decimal] = mapped_column(Numeric)
    applies_when: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    state: Mapped[str]
    effective_from: Mapped[date]
    effective_to: Mapped[date | None]
    source: Mapped[str]
    verified_by: Mapped[str | None]
    verified_on: Mapped[date | None]


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    owner_type: Mapped[str]
    owner_id: Mapped[UUID | None]
    storage_path: Mapped[str]
    mime: Mapped[str]
    size_bytes: Mapped[int]
    sha256: Mapped[str]
    original_filename: Mapped[str | None]
    uploaded_by: Mapped[UUID | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    kind: Mapped[str]
    attachment_id: Mapped[UUID | None]
    status: Mapped[str]
    row_count: Mapped[int] = mapped_column(server_default="0")
    ok_count: Mapped[int] = mapped_column(server_default="0")
    error_count: Mapped[int] = mapped_column(server_default="0")
    preview: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    created_by: Mapped[UUID | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
