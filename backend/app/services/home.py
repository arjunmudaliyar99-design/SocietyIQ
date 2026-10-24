"""Committee home (docs/02 §10): the cards and "What needs your attention".

Cards that depend on a module not built yet are listed in "coming_soon" (none now) so the
screen shape stays final while numbers arrive later. Figures are
counts and dates from the database, never estimates.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.billing import period_start_for
from app.models import BillingRun, Complaint, Payment, Society
from app.services import compliance as compliance_service
from app.services import payments as payment_service

# Modules whose cards are not live yet. Remove a key when its milestone is on dev.
COMING_SOON: tuple[str, ...] = ()
# Same as "Waiting for you" on the Payments page (M6).
WAITING_STATUSES = ("pending", "recorded")
# Complaints still waiting on the committee; resolved ones wait on the resident, not on them.
OPEN_COMPLAINT_STATUSES = ("open", "in_progress")
ATTENTION_LIMIT = 8


def next_bill_date(today: date, bill_day: int | None, frequency: str, fy_start: int) -> date | None:
    """The next day the billing job will run (app/jobs/billing): a month that has the bill day,
    and for quarterly billing a month that starts a quarter."""
    if not bill_day:
        return None
    month_start = today.replace(day=1)
    for _ in range(13):
        try:
            candidate = month_start.replace(day=bill_day)
        except ValueError:
            candidate = None
        if (
            candidate
            and candidate >= today
            and period_start_for(candidate, frequency, fy_start) is not None
        ):
            return candidate
        month_start = (month_start + timedelta(days=32)).replace(day=1)
    return None


@dataclass
class Home:
    coming_soon: tuple[str, ...]
    open_complaints: int
    collected_paise: int
    collected_count: int
    outstanding_paise: int
    flats_with_dues: int
    payments_waiting: int
    compliance_overdue: int
    compliance_due_soon: int
    next_bill_date: date | None
    latest_run: BillingRun | None
    attention: list[dict[str, Any]] = field(default_factory=list)


async def home(session: AsyncSession, society_id: UUID, today: date) -> Home:
    society = await session.get(Society, society_id)
    assert society is not None  # require_role already confirmed membership
    items = await compliance_service.list_items(session, society_id, today, active_only=True)
    overdue = [v for v in items if v.status == "overdue"]
    due_soon = [v for v in items if v.status == "due_soon"]
    latest_run = await session.scalar(
        select(BillingRun)
        .where(BillingRun.society_id == society_id, BillingRun.status != "cancelled")
        .order_by(BillingRun.period_start.desc(), BillingRun.created_at.desc())
        .limit(1)
    )

    open_complaints = await session.scalar(
        select(func.count())
        .select_from(Complaint)
        .where(Complaint.society_id == society_id, Complaint.status.in_(OPEN_COMPLAINT_STATUSES))
    )

    month_start = today.replace(day=1)
    collected = await payment_service.collected_between(session, society_id, month_start, today)
    collected_count = await session.scalar(
        select(func.count())
        .select_from(Payment)
        .where(
            Payment.society_id == society_id,
            Payment.status == "confirmed",
            Payment.received_on >= month_start,
            Payment.received_on <= today,
        )
    )
    dues = await payment_service.dues(session, society_id)
    waiting = await session.scalar(
        select(func.count())
        .select_from(Payment)
        .where(Payment.society_id == society_id, Payment.status.in_(WAITING_STATUSES))
    )

    attention: list[dict[str, Any]] = []
    if waiting:
        attention.append(
            {
                "key": "home.attention.paymentsWaiting",
                "params": {"count": waiting},
                "link": "/payments",
            }
        )
    if latest_run is not None and latest_run.status == "draft":
        attention.append(
            {
                "key": "home.attention.runWaiting",
                "params": {"period": latest_run.period_start.isoformat()},
                "link": f"/bills/runs/{latest_run.id}",
            }
        )
    for v in overdue:
        attention.append(
            {
                "key": "home.attention.overdue",
                "params": {"title": v.item.title, "days": -v.days_left},
                "link": f"/compliance/{v.item.id}",
            }
        )
    for v in due_soon:
        attention.append(
            {
                "key": "home.attention.dueSoon",
                "params": {"title": v.item.title, "date": v.item.next_due_on.isoformat()},
                "link": f"/compliance/{v.item.id}",
            }
        )

    return Home(
        coming_soon=COMING_SOON,
        open_complaints=open_complaints or 0,
        collected_paise=collected,
        collected_count=collected_count or 0,
        # Advances are not netted off, as on the Dues page.
        outstanding_paise=sum(max(d.balance_paise, 0) for d in dues),
        flats_with_dues=sum(1 for d in dues if d.balance_paise > 0),
        payments_waiting=waiting or 0,
        compliance_overdue=len(overdue),
        compliance_due_soon=len(due_soon),
        next_bill_date=next_bill_date(
            today, society.bill_day, society.billing_frequency, society.financial_year_start_month
        ),
        latest_run=latest_run,
        attention=attention[:ATTENTION_LIMIT],
    )
