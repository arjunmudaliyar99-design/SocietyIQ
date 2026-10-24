"""compliance_reminders (docs/04 §13): daily; records the reminders due today per docs/06 §9.

Idempotent: one row per (item, due date, step), inserted with ON CONFLICT DO NOTHING, so a
second run on the same day adds nothing. Reminders go to the committee only (docs/02 §13).
Email delivery waits for the notify service (M9); until then the rows are the record of what
is to be sent, and the committee home shows overdue and due-soon items directly.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from app.calc.compliance import reminder_today
from app.db import get_sessionmaker, set_society_context
from app.models import ComplianceItem, ComplianceReminder, JobRun, Society

JOB_NAME = "compliance_reminders"


@dataclass
class ReminderReport:
    created: int = 0
    societies: int = 0
    failed: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"created": self.created, "societies": self.societies, "failed": self.failed}


async def _society_ids() -> list[UUID]:
    async with get_sessionmaker()() as session, session.begin():
        # Read-only scheduler view of societies (policy scheduler_read, migration 0004).
        await session.execute(text("SELECT set_config('app.job', 'scheduler', true)"))
        return list(await session.scalars(select(Society.id)))


async def _for_society(society_id: UUID, today: date) -> int:
    created = 0
    async with get_sessionmaker()() as session, session.begin():
        await set_society_context(session, society_id)
        items = await session.scalars(
            select(ComplianceItem).where(
                ComplianceItem.society_id == society_id, ComplianceItem.is_active
            )
        )
        for item in items:
            step = reminder_today(item.next_due_on, today)
            if step is None:
                continue
            result = await session.execute(
                insert(ComplianceReminder)
                .values(
                    society_id=society_id,
                    compliance_item_id=item.id,
                    due_on=item.next_due_on,
                    days_before=step,
                )
                .on_conflict_do_nothing()
                .returning(ComplianceReminder.id)
            )
            created += len(result.all())
    return created


async def compliance_reminders(today: date) -> ReminderReport:
    report = ReminderReport()
    started = datetime.now(UTC)
    for society_id in await _society_ids():
        report.societies += 1
        try:
            report.created += await _for_society(society_id, today)
        except Exception as exc:  # noqa: BLE001 — one society must not stop the others
            report.failed[str(society_id)] = type(exc).__name__
    async with get_sessionmaker()() as session, session.begin():
        session.add(
            JobRun(
                job_name=JOB_NAME,
                started_at=started,
                finished_at=datetime.now(UTC),
                status="failed" if report.failed else "succeeded",
                details={"today": str(today), **report.as_dict()},
            )
        )
    return report
