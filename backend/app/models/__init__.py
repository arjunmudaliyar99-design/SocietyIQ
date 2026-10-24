"""SQLAlchemy models, one file per domain (docs/05). Tables are created only by Alembic."""

from app.models.base import Base
from app.models.flats import Wing
from app.models.people import Consent, Society, SocietyMembership, User
from app.models.system import AuditLog, LegalParameter

__all__ = [
    "AuditLog",
    "Base",
    "Consent",
    "LegalParameter",
    "Society",
    "SocietyMembership",
    "User",
    "Wing",
]
