"""SQLAlchemy models, one file per domain (docs/05). Tables are created only by Alembic."""

from app.models.base import Base
from app.models.billing import Bill, BillingRun, BillLine, JobRun, NumberSequence
from app.models.charges import (
    ChargeHead,
    FlatChargeOverride,
    ParkingAllotment,
    PropertyTaxAssessment,
)
from app.models.flats import Flat, Member, Wing
from app.models.ledger import LedgerEntry
from app.models.people import Consent, Society, SocietyMembership, User
from app.models.system import Attachment, AuditLog, ImportJob, LegalParameter

__all__ = [
    "Attachment",
    "AuditLog",
    "Base",
    "Bill",
    "BillLine",
    "BillingRun",
    "ChargeHead",
    "Consent",
    "Flat",
    "FlatChargeOverride",
    "ImportJob",
    "JobRun",
    "LedgerEntry",
    "LegalParameter",
    "Member",
    "NumberSequence",
    "ParkingAllotment",
    "PropertyTaxAssessment",
    "Society",
    "SocietyMembership",
    "User",
    "Wing",
]
