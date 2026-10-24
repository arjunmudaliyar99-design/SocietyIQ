"""SQLAlchemy models, one file per domain (docs/05). Tables are created only by Alembic."""

from app.models.base import Base
from app.models.flats import Flat, Member, Wing
from app.models.ledger import LedgerEntry
from app.models.people import Consent, Society, SocietyMembership, User
from app.models.system import Attachment, AuditLog, ImportJob, LegalParameter

__all__ = [
    "Attachment",
    "AuditLog",
    "Base",
    "Consent",
    "Flat",
    "ImportJob",
    "LedgerEntry",
    "LegalParameter",
    "Member",
    "Society",
    "SocietyMembership",
    "User",
    "Wing",
]
