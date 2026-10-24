"""Billing runs and bills (docs/02 §5, docs/06 §3, §5).

Draft: the per-flat charges for the period, frozen in a snapshot for review. Approve: one
transaction that re-checks the snapshot against the current setup, takes gap-free numbers,
writes bills, lines, ledger entries and the audit log. A bill is never edited: it is
cancelled with a reason (reversal entries) and reissued.

PDFs are rendered from the saved bill when first asked for (app/pdf), so a renderer problem
can never block or roll back the money records.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calc.bills import OverdueBill, bill_figures, bill_number, interest_on_overdue
from app.errors import AppError, not_found
from app.models import (
    Bill,
    BillingRun,
    BillLine,
    Flat,
    LedgerEntry,
    Member,
    NumberSequence,
    Society,
    User,
    Wing,
)
from app.services import audit, ledger
from app.services import charges as charge_service

EPOCH = date(1970, 1, 1)


def _heads_config(preview: charge_service.Preview) -> list[dict[str, Any]]:
    keys = (
        "id",
        "name",
        "calc_type",
        "standard_code",
        "period_total_paise",
        "fixed_amount_paise",
        "percent",
        "percent_of_head_id",
        "applies_to",
        "frequency",
        "one_time_period",
        "sort_order",
    )
    return [
        {
            k: (str(v) if isinstance(v, UUID | Decimal | date) else v)
            for k, v in ((k, getattr(h, k)) for k in keys)
        }
        for h in preview.heads
    ]


def _snapshot(preview: charge_service.Preview) -> dict[str, Any]:
    heads = _heads_config(preview)
    # A list, not an object: jsonb does not keep key order, and bill numbers follow flat order.
    flats = [
        {
            "flat_id": fid,
            "label": preview.flats[fid].label,
            "lines": lines,
            "rounding": preview.rounding[fid],
            "charges": preview.result.totals[fid] + preview.rounding[fid],
        }
        for fid, lines in preview.result.by_flat.items()
    ]
    config = json.dumps(heads, sort_keys=True)
    return {
        "heads": heads,
        "flats": flats,
        "excluded": {fid: r for fid, r in preview.result.excluded.items()},
        "config_hash": hashlib.sha256(config.encode()).hexdigest(),
    }


async def _member_names(session: AsyncSession, society_id: UUID) -> dict[UUID, str]:
    rows = await session.execute(
        select(Member.flat_id, Member.full_name)
        .where(Member.society_id == society_id, Member.to_date.is_(None))
        .order_by(Member.flat_id, Member.is_primary.desc(), Member.created_at)
    )
    names: dict[UUID, str] = {}
    for flat_id, name in rows:
        names.setdefault(flat_id, name)
    return names


def _warnings(preview: charge_service.Preview, members: dict[UUID, str]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for fid, reasons in preview.result.excluded.items():
        warnings.append(
            {"key": "flatLeftOut", "flat": preview.flats[fid].label, "reasons": reasons}
        )
    for fid in preview.result.by_flat:
        label = preview.flats[fid].label
        if UUID(fid) not in members:
            warnings.append({"key": "noMember", "flat": label})
        if preview.result.totals[fid] + preview.rounding[fid] == 0:
            warnings.append({"key": "zeroAmount", "flat": label})
    if not preview.heads:
        warnings.append({"key": "noCharges"})
    return warnings


async def get_society_or_404(session: AsyncSession, society_id: UUID) -> Society:
    society = await session.get(Society, society_id)
    if society is None:
        raise not_found()
    return society


async def live_run_for(
    session: AsyncSession, society_id: UUID, period_start: date
) -> BillingRun | None:
    return await session.scalar(
        select(BillingRun).where(
            BillingRun.society_id == society_id,
            BillingRun.period_start == period_start,
            BillingRun.status != "cancelled",
        )
    )


async def create_draft(
    session: AsyncSession,
    society_id: UUID,
    actor: User | None,
    period_start: date,
    by_job: bool = False,
) -> BillingRun:
    society = await get_society_or_404(session, society_id)
    if society.bill_day is None:
        raise AppError(422, "BILL_DAY_MISSING", "errors.billDayMissing")
    if await live_run_for(session, society_id, period_start):
        raise AppError(409, "RUN_EXISTS", "errors.runExists")

    preview = await charge_service.preview(session, society_id, period_start)
    if not preview.heads:
        raise AppError(422, "NO_CHARGES", "errors.noCharges")
    members = await _member_names(session, society_id)
    snapshot = _snapshot(preview)
    bill_date = preview.period.start.replace(day=society.bill_day)
    run = BillingRun(
        society_id=society_id,
        period_start=preview.period.start,
        period_end=preview.period.end,
        bill_date=bill_date,
        due_date=bill_date + timedelta(days=society.due_days),
        status="draft",
        flat_count=len(snapshot["flats"]),
        total_paise=sum(f["charges"] for f in snapshot["flats"]),
        warnings=_warnings(preview, members),
        charges_snapshot=snapshot,
        created_by_job=by_job,
        created_by=actor.id if actor else None,
    )
    session.add(run)
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id if actor else None,
        action="billing_run.create",
        entity_type="billing_run",
        entity_id=run.id,
        after={
            "period_start": str(run.period_start),
            "flat_count": run.flat_count,
            "total_paise": run.total_paise,
            "by_job": by_job,
        },
    )
    await session.refresh(run)
    return run


async def get_run(session: AsyncSession, society_id: UUID, run_id: UUID) -> BillingRun:
    run = await session.get(BillingRun, run_id)
    if run is None or run.society_id != society_id:
        raise not_found()
    return run


async def list_runs(session: AsyncSession, society_id: UUID) -> list[BillingRun]:
    rows = await session.scalars(
        select(BillingRun)
        .where(BillingRun.society_id == society_id)
        .order_by(BillingRun.period_start.desc(), BillingRun.created_at.desc())
    )
    return list(rows)


async def cancel_draft(
    session: AsyncSession, society_id: UUID, actor: User, run_id: UUID, reason: str
) -> BillingRun:
    run = await get_run(session, society_id, run_id)
    if run.status != "draft":
        raise AppError(409, "RUN_NOT_DRAFT", "errors.runNotDraft")
    run.status = "cancelled"
    run.cancelled_reason = reason
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="billing_run.cancel",
        entity_type="billing_run",
        entity_id=run.id,
        reason=reason,
    )
    return run


async def _reserve_numbers(
    session: AsyncSession, society_id: UUID, financial_year: str, count: int
) -> int:
    """Gap-free numbering (docs/05 §3): lock the sequence row for the rest of the money
    transaction and take `count` numbers in one go. Returns the first."""
    seq = await session.scalar(
        select(NumberSequence)
        .where(
            NumberSequence.society_id == society_id,
            NumberSequence.kind == "bill",
            NumberSequence.financial_year == financial_year,
        )
        .with_for_update()
    )
    if seq is None:
        seq = NumberSequence(
            society_id=society_id, kind="bill", financial_year=financial_year, next_value=1
        )
        session.add(seq)
        await session.flush()
    first = seq.next_value
    seq.next_value = first + count
    return first


async def _interest_by_flat(
    session: AsyncSession,
    society: Society,
    flat_ids: list[UUID],
    bill_date: date,
    charged_through: date,
) -> dict[UUID, int]:
    result = {fid: 0 for fid in flat_ids}
    if not society.interest_enabled or not society.interest_rate_annual_pct or not flat_ids:
        return result
    # Unpaid charges of earlier bills. Payments arrive in M6 and will reduce the principal.
    rows = await session.execute(
        select(Bill.flat_id, Bill.charges_paise, Bill.due_date).where(
            Bill.flat_id.in_(flat_ids),
            Bill.status.in_(("issued", "partially_paid")),
            Bill.bill_date < bill_date,
        )
    )
    overdue: dict[UUID, list[OverdueBill]] = {}
    for flat_id, principal, due in rows:
        overdue.setdefault(flat_id, []).append(OverdueBill(principal, due))
    for flat_id, bills in overdue.items():
        result[flat_id] = interest_on_overdue(
            bills,
            Decimal(society.interest_rate_annual_pct),
            society.interest_grace_days or 0,
            charged_through,
            bill_date,
        )
    return result


async def _charged_through(session: AsyncSession, society_id: UUID, bill_date: date) -> date:
    """Interest is charged up to each approved run's bill date, so never counted twice."""
    last = await session.scalar(
        select(func.max(BillingRun.bill_date)).where(
            BillingRun.society_id == society_id,
            BillingRun.status.in_(("approved", "sent")),
            BillingRun.bill_date < bill_date,
        )
    )
    return last or EPOCH


@dataclass
class _FlatCharges:
    label: str
    lines: dict[str, int]
    rounding: int


async def _issue_bill(
    session: AsyncSession,
    *,
    society: Society,
    run: BillingRun,
    flat_id: UUID,
    charges: _FlatCharges,
    head_names: dict[str, str],
    head_order: list[str],
    member_name: str | None,
    number: str,
    balance_before: int,
    interest: int,
    actor: User | None,
    replaces: Bill | None = None,
) -> Bill:
    """Adds the bill, its lines, ledger entries and audit row to the session without a round
    trip each; the caller flushes once."""
    charges_paise = sum(charges.lines.values()) + charges.rounding
    figures = bill_figures(charges_paise, balance_before, interest)
    bill = Bill(
        id=uuid4(),
        society_id=society.id,
        billing_run_id=run.id,
        flat_id=flat_id,
        bill_number=number,
        period_start=run.period_start,
        period_end=run.period_end,
        bill_date=run.bill_date,
        due_date=run.due_date,
        charges_paise=figures.charges_paise,
        arrears_paise=figures.arrears_paise,
        advance_paise=figures.advance_paise,
        interest_paise=figures.interest_paise,
        total_due_paise=figures.total_due_paise,
        status="issued",
        replaces_bill_id=replaces.id if replaces else None,
        language=society.default_language,
        member_name=member_name,
        created_by=actor.id if actor else None,
    )
    session.add(bill)

    order = 0
    for head_id in head_order:
        amount = charges.lines.get(head_id, 0)
        if amount:
            order += 1
            session.add(
                BillLine(
                    bill_id=bill.id,
                    society_id=society.id,
                    charge_head_id=UUID(head_id),
                    description=head_names[head_id],
                    amount_paise=amount,
                    sort_order=order,
                )
            )
    if charges.rounding:
        session.add(
            BillLine(
                bill_id=bill.id,
                society_id=society.id,
                line_type="rounding",
                description="Rounding off",
                amount_paise=charges.rounding,
                sort_order=order + 1,
            )
        )
    if interest:
        session.add(
            BillLine(
                bill_id=bill.id,
                society_id=society.id,
                line_type="interest",
                description="Interest on overdue dues",
                amount_paise=interest,
                sort_order=order + 2,
            )
        )

    if charges_paise:
        session.add(
            LedgerEntry(
                society_id=society.id,
                flat_id=flat_id,
                entry_date=run.bill_date,
                entry_type="bill",
                amount_paise=charges_paise,
                source_type="bill",
                source_id=bill.id,
                created_by=actor.id if actor else None,
            )
        )
    if interest:
        session.add(
            LedgerEntry(
                society_id=society.id,
                flat_id=flat_id,
                entry_date=run.bill_date,
                entry_type="interest",
                amount_paise=interest,
                source_type="bill",
                source_id=bill.id,
                created_by=actor.id if actor else None,
            )
        )
    await audit.record(
        session,
        flush=False,
        society_id=society.id,
        actor_user_id=actor.id if actor else None,
        action="bill.reissue" if replaces else "bill.issue",
        entity_type="bill",
        entity_id=bill.id,
        after={
            "bill_number": number,
            "flat": charges.label,
            "charges_paise": figures.charges_paise,
            "arrears_paise": figures.arrears_paise,
            "advance_paise": figures.advance_paise,
            "interest_paise": figures.interest_paise,
            "total_due_paise": figures.total_due_paise,
            "replaces_bill_id": str(replaces.id) if replaces else None,
        },
    )
    return bill


def _flat_charges(snapshot_flat: dict[str, Any]) -> _FlatCharges:
    return _FlatCharges(snapshot_flat["label"], snapshot_flat["lines"], snapshot_flat["rounding"])


async def approve(
    session: AsyncSession, society_id: UUID, actor: User | None, run_id: UUID
) -> BillingRun:
    run = await get_run(session, society_id, run_id)
    if run.status != "draft":
        raise AppError(409, "RUN_NOT_DRAFT", "errors.runNotDraft")
    society = await get_society_or_404(session, society_id)

    # What is approved must be exactly what was reviewed.
    fresh = _snapshot(await charge_service.preview(session, society_id, run.period_start))
    if {k: fresh[k] for k in ("heads", "flats", "excluded")} != {
        k: run.charges_snapshot.get(k) for k in ("heads", "flats", "excluded")
    }:
        raise AppError(409, "RUN_STALE", "errors.runStale")

    snapshot = run.charges_snapshot
    head_order = [h["id"] for h in snapshot["heads"]]
    head_names = {h["id"]: h["name"] for h in snapshot["heads"]}
    members = await _member_names(session, society_id)
    fy = charge_service.financial_year(run.bill_date, society.financial_year_start_month)
    charged_through = await _charged_through(session, society_id, run.bill_date)
    flat_ids = [UUID(f["flat_id"]) for f in snapshot["flats"]]
    balances = await ledger.balances(session, flat_ids)
    interest = await _interest_by_flat(session, society, flat_ids, run.bill_date, charged_through)
    first = await _reserve_numbers(session, society_id, fy, len(flat_ids))

    total = 0
    for offset, data in enumerate(snapshot["flats"]):  # flat-number order
        flat_id = UUID(data["flat_id"])
        bill = await _issue_bill(
            session,
            society=society,
            run=run,
            flat_id=flat_id,
            charges=_flat_charges(data),
            head_names=head_names,
            head_order=head_order,
            member_name=members.get(flat_id),
            number=bill_number(fy, first + offset),
            balance_before=balances[flat_id],
            interest=interest[flat_id],
            actor=actor,
        )
        total += bill.charges_paise + bill.interest_paise
    await session.flush()

    run.status = "approved"
    run.approved_by = actor.id if actor else None
    run.approved_at = datetime.now(UTC)
    run.total_paise = total
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id if actor else None,
        action="billing_run.approve",
        entity_type="billing_run",
        entity_id=run.id,
        after={"flat_count": run.flat_count, "total_paise": total, "auto": actor is None},
    )
    await session.refresh(run)
    return run


async def get_bill(session: AsyncSession, society_id: UUID, bill_id: UUID) -> Bill:
    bill = await session.get(Bill, bill_id)
    if bill is None or bill.society_id != society_id:
        raise not_found()
    return bill


async def bill_lines(session: AsyncSession, bill_id: UUID) -> list[BillLine]:
    rows = await session.scalars(
        select(BillLine).where(BillLine.bill_id == bill_id).order_by(BillLine.sort_order)
    )
    return list(rows)


async def flat_labels(session: AsyncSession, society_id: UUID) -> dict[UUID, str]:
    wings = list(await session.scalars(select(Wing).where(Wing.society_id == society_id)))
    by_id = {w.id: w for w in wings}
    rows = await session.execute(
        select(Flat.id, Flat.wing_id, Flat.flat_number).where(Flat.society_id == society_id)
    )
    return {
        fid: (f"{by_id[wid].name}-{number}" if len(wings) > 1 else number)
        for fid, wid, number in rows
    }


async def list_bills(
    session: AsyncSession, society_id: UUID, run_id: UUID | None = None, flat_id: UUID | None = None
) -> list[Bill]:
    query = select(Bill).where(Bill.society_id == society_id)
    if run_id:
        query = query.where(Bill.billing_run_id == run_id)
    if flat_id:
        query = query.where(Bill.flat_id == flat_id)
    return list(await session.scalars(query.order_by(Bill.bill_date.desc(), Bill.bill_number)))


async def cancel_bill(
    session: AsyncSession, society_id: UUID, actor: User, bill_id: UUID, reason: str
) -> Bill:
    """Never edit a sent bill: cancel it with a reason and reverse its ledger entries."""
    bill = await get_bill(session, society_id, bill_id)
    if bill.status != "issued":
        # Paid or partly paid bills need their payments reversed first (M6).
        raise AppError(409, "BILL_NOT_CANCELLABLE", "errors.billNotCancellable")
    entries = list(
        await session.scalars(
            select(LedgerEntry).where(
                LedgerEntry.source_type == "bill",
                LedgerEntry.source_id == bill.id,
                LedgerEntry.entry_type.in_(("bill", "interest")),
            )
        )
    )
    for entry in entries:
        session.add(
            LedgerEntry(
                society_id=society_id,
                flat_id=bill.flat_id,
                entry_date=bill.bill_date,
                entry_type="reversal",
                amount_paise=-entry.amount_paise,
                source_type="bill",
                source_id=bill.id,
                reverses_entry_id=entry.id,
                reason=reason,
                created_by=actor.id,
            )
        )
    bill.status = "cancelled"
    bill.cancelled_reason = reason
    bill.cancelled_at = datetime.now(UTC)
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="bill.cancel",
        entity_type="bill",
        entity_id=bill.id,
        before={"status": "issued", "total_due_paise": bill.total_due_paise},
        after={"status": "cancelled", "reversed_paise": sum(-e.amount_paise for e in entries)},
        reason=reason,
    )
    return bill


async def reissue_bill(session: AsyncSession, society_id: UUID, actor: User, bill_id: UUID) -> Bill:
    """A corrected bill for the same flat and period, from the charge setup as it is now."""
    old = await get_bill(session, society_id, bill_id)
    if old.status != "cancelled":
        raise AppError(409, "BILL_NOT_CANCELLED", "errors.billNotCancelled")
    already = await session.scalar(select(Bill.id).where(Bill.replaces_bill_id == old.id))
    if already:
        raise AppError(409, "BILL_ALREADY_REISSUED", "errors.billAlreadyReissued")
    run = await get_run(session, society_id, old.billing_run_id)
    society = await get_society_or_404(session, society_id)
    preview = await charge_service.preview(session, society_id, run.period_start)
    fid = str(old.flat_id)
    if fid not in preview.result.by_flat:
        raise AppError(422, "FLAT_LEFT_OUT", "errors.flatLeftOut")
    snapshot = _snapshot(preview)
    flat_data = next(f for f in snapshot["flats"] if f["flat_id"] == fid)
    members = await _member_names(session, society_id)
    fy = charge_service.financial_year(run.bill_date, society.financial_year_start_month)
    charged_through = await _charged_through(session, society_id, run.bill_date)
    interest = await _interest_by_flat(
        session, society, [old.flat_id], run.bill_date, charged_through
    )
    bill = await _issue_bill(
        session,
        society=society,
        run=run,
        flat_id=old.flat_id,
        charges=_flat_charges(flat_data),
        head_names={h["id"]: h["name"] for h in snapshot["heads"]},
        head_order=[h["id"] for h in snapshot["heads"]],
        member_name=members.get(old.flat_id),
        number=bill_number(fy, await _reserve_numbers(session, society_id, fy, 1)),
        balance_before=(await ledger.balances(session, [old.flat_id]))[old.flat_id],
        interest=interest[old.flat_id],
        actor=actor,
        replaces=old,
    )
    await session.flush()
    return bill


def config_hash(run: BillingRun) -> str | None:
    return run.charges_snapshot.get("config_hash")


async def last_approved(session: AsyncSession, society_id: UUID, before: date) -> BillingRun | None:
    return await session.scalar(
        select(BillingRun)
        .where(
            BillingRun.society_id == society_id,
            BillingRun.status.in_(("approved", "sent")),
            BillingRun.period_start < before,
        )
        .order_by(BillingRun.period_start.desc())
        .limit(1)
    )
