"""create_draft_billing_runs (docs/04 §13): daily; drafts for societies whose bill day is today.

Idempotent: a period with a live run is skipped (and a unique index guards it too). Each
society runs in its own transaction, so one failing society does not stop the others. When a
society turned on auto-approve and its charge setup is unchanged since the last approved run,
the draft is approved straight away (docs/02 §5 point 5).
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, text

from app.db import get_sessionmaker, set_society_context
from app.errors import AppError
from app.models import JobRun, Society
from app.services import billing

JOB_NAME = "create_draft_billing_runs"


def period_start_for(today: date, frequency: str, fy_start_month: int) -> date | None:
    """Monthly: this month. Quarterly: only in a month that starts a quarter of the society's
    financial year. TODO(confirm): Q-007 — any other quarterly rules."""
    if frequency == "quarterly" and (today.month - fy_start_month) % 3 != 0:
        return None
    return today.replace(day=1)


@dataclass
class JobReport:
    created: list[str] = field(default_factory=list)
    approved: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "approved": self.approved,
            "skipped": self.skipped,
            "failed": self.failed,
        }


async def _due_societies(today: date) -> list[tuple[UUID, str, int, bool]]:
    async with get_sessionmaker()() as session, session.begin():
        # Read-only scheduler view of societies (policy scheduler_read, migration 0004).
        await session.execute(text("SELECT set_config('app.job', 'scheduler', true)"))
        rows = await session.execute(
            select(
                Society.id,
                Society.billing_frequency,
                Society.financial_year_start_month,
                Society.auto_approve_billing,
            ).where(Society.bill_day == today.day)
        )
        return [tuple(r) for r in rows]  # type: ignore[misc]


async def _record(run: JobRun) -> None:
    async with get_sessionmaker()() as session, session.begin():
        await session.merge(run)


async def create_draft_billing_runs(today: date) -> JobReport:
    report = JobReport()
    job = JobRun(job_name=JOB_NAME, status="running", details={"today": str(today)})
    async with get_sessionmaker()() as session, session.begin():
        session.add(job)
        await session.flush()
        job_id = job.id

    for society_id, frequency, fy_start, auto in await _due_societies(today):
        period = period_start_for(today, frequency, fy_start)
        key = str(society_id)
        if period is None:
            report.skipped.append(key)
            continue
        try:
            async with get_sessionmaker()() as session, session.begin():
                await set_society_context(session, society_id)
                if await billing.live_run_for(session, society_id, period):
                    report.skipped.append(key)
                    continue
                run = await billing.create_draft(session, society_id, None, period, by_job=True)
                report.created.append(key)
                previous = await billing.last_approved(session, society_id, period)
                if auto and previous and billing.config_hash(previous) == billing.config_hash(run):
                    await billing.approve(session, society_id, None, run.id)
                    report.approved.append(key)
        except AppError as exc:
            report.failed[key] = exc.code

    await _record(
        JobRun(
            id=job_id,
            job_name=JOB_NAME,
            status="failed" if report.failed else "succeeded",
            finished_at=datetime.now(UTC),
            details={"today": str(today), **report.as_dict()},
        )
    )
    return report
