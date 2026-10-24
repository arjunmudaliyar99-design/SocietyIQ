"""Payments, receipts, allocation and dues (docs/02 §6-7, docs/06 §4, §6).

A payment touches the ledger only when confirmed. Allocation is a reconciliation step: after a
payment is confirmed or reversed, or a bill is issued, every confirmed payment's unallocated
amount settles the flat's oldest unpaid items (opening balance first, then bills by date).
Nothing is deleted: a reversal adds rows and marks allocations and the receipt as undone.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calc.payments import DueItem, allocate, bucket_for, opening_months_left
from app.errors import AppError, not_found
from app.models import (
    Bill,
    Flat,
    LedgerEntry,
    Payment,
    PaymentAllocation,
    Receipt,
    Society,
    User,
)
from app.services import audit, ledger, numbers
from app.services.charges import financial_year
from app.timeutil import today_ist

PAYMENT_FIELDS = (
    "flat_id",
    "amount_paise",
    "method",
    "status",
    "received_on",
    "reference",
    "cheque_bank",
    "cheque_date",
    "reported_by_resident",
    "notes",
    "reason",
)


def _snap(payment: Payment) -> dict[str, Any]:
    return {
        k: (str(v) if isinstance(v, UUID | date) else v)
        for k, v in ((k, getattr(payment, k)) for k in PAYMENT_FIELDS)
    }


# --- what a flat still owes, item by item ---------------------------------------------


@dataclass
class OpenItem:
    kind: str  # "opening" or "bill"
    id: UUID
    due_on: date
    original_paise: int
    unpaid_paise: int
    months: int | None = None


async def _allocated(session: AsyncSession, flat_ids: list[UUID]) -> dict[UUID, int]:
    """Active allocations per bill id and per opening-balance ledger entry id."""
    target = func.coalesce(PaymentAllocation.bill_id, PaymentAllocation.ledger_entry_id)
    rows = await session.execute(
        select(target, func.sum(PaymentAllocation.amount_paise))
        .join(Payment, Payment.id == PaymentAllocation.payment_id)
        .where(Payment.flat_id.in_(flat_ids), PaymentAllocation.reversed_at.is_(None))
        .group_by(target)
    )
    return {key: int(total) for key, total in rows}


async def open_items(session: AsyncSession, flat_ids: list[UUID]) -> dict[UUID, list[OpenItem]]:
    """Opening balances and live bills per flat, with what is still unpaid. An opening balance
    is the oldest debt, so it is dated before every bill."""
    result: dict[UUID, list[OpenItem]] = {fid: [] for fid in flat_ids}
    if not flat_ids:
        return result
    allocated = await _allocated(session, flat_ids)
    openings = await session.scalars(
        select(LedgerEntry).where(
            LedgerEntry.flat_id.in_(flat_ids),
            LedgerEntry.entry_type == "opening_balance",
            LedgerEntry.amount_paise > 0,
        )
    )
    for entry in openings:
        result[entry.flat_id].append(
            OpenItem(
                "opening",
                entry.id,
                date.min,
                entry.amount_paise,
                max(entry.amount_paise - allocated.get(entry.id, 0), 0),
                entry.months_pending,
            )
        )
    bills = await session.scalars(
        select(Bill)
        .where(Bill.flat_id.in_(flat_ids), Bill.status != "cancelled")
        .order_by(Bill.bill_date, Bill.bill_number)
    )
    for bill in bills:
        owed = bill.charges_paise + bill.interest_paise
        result[bill.flat_id].append(
            OpenItem(
                "bill", bill.id, bill.bill_date, owed, max(owed - allocated.get(bill.id, 0), 0)
            )
        )
    return result


def months_pending(items: list[OpenItem]) -> int:
    total = 0
    for item in items:
        if item.kind == "opening":
            total += opening_months_left(item.original_paise, item.months, item.unpaid_paise)
        elif item.unpaid_paise > 0:
            total += 1
    return total


# --- reconciliation -------------------------------------------------------------------


async def _sync_bill_statuses(session: AsyncSession, flat_id: UUID) -> None:
    items = {i.id: i for i in (await open_items(session, [flat_id]))[flat_id] if i.kind == "bill"}
    for bill in await session.scalars(
        select(Bill).where(Bill.flat_id == flat_id, Bill.status != "cancelled")
    ):
        item = items[bill.id]
        if item.original_paise > 0 and item.unpaid_paise == 0:
            status = "paid"
        elif item.unpaid_paise < item.original_paise:
            status = "partially_paid"
        else:
            status = "issued"
        if bill.status != status:
            bill.status = status


async def reconcile(session: AsyncSession, society_id: UUID, flat_id: UUID) -> None:
    """Settle the flat's oldest unpaid items with any confirmed money not yet allocated."""
    payments = list(
        await session.scalars(
            select(Payment)
            .where(Payment.flat_id == flat_id, Payment.status == "confirmed")
            .order_by(Payment.confirmed_at, Payment.created_at)
        )
    )
    used: dict[UUID, int] = {}
    if payments:
        rows = await session.execute(
            select(PaymentAllocation.payment_id, func.sum(PaymentAllocation.amount_paise))
            .where(
                PaymentAllocation.payment_id.in_([p.id for p in payments]),
                PaymentAllocation.reversed_at.is_(None),
            )
            .group_by(PaymentAllocation.payment_id)
        )
        used = {pid: int(total) for pid, total in rows}
    for payment in payments:
        free = payment.amount_paise - used.get(payment.id, 0)
        if free <= 0:
            continue
        items = (await open_items(session, [flat_id]))[flat_id]
        due = [DueItem(f"{i.kind}:{i.id}", i.due_on, i.unpaid_paise) for i in items]
        if not any(d.unpaid_paise for d in due):
            break
        for key, amount in allocate(due, free).allocations:
            kind, raw = key.split(":", 1)
            session.add(
                PaymentAllocation(
                    society_id=society_id,
                    payment_id=payment.id,
                    bill_id=UUID(raw) if kind == "bill" else None,
                    ledger_entry_id=UUID(raw) if kind == "opening" else None,
                    amount_paise=amount,
                )
            )
        await session.flush()
    await _sync_bill_statuses(session, flat_id)
    await session.flush()


# --- payments -------------------------------------------------------------------------


async def get_payment(session: AsyncSession, society_id: UUID, payment_id: UUID) -> Payment:
    payment = await session.get(Payment, payment_id)
    if payment is None or payment.society_id != society_id:
        raise not_found()
    return payment


async def record(
    session: AsyncSession,
    society_id: UUID,
    actor: User,
    fields: dict[str, Any],
    *,
    by_resident: bool = False,
    confirm_now: bool = False,
) -> Payment:
    flat = await session.get(Flat, fields["flat_id"])
    if flat is None or flat.society_id != society_id:
        raise not_found()
    if fields["method"] == "cheque" and not fields.get("reference"):
        raise AppError(422, "CHEQUE_NUMBER_REQUIRED", "errors.chequeNumberRequired")
    if confirm_now and fields["method"] == "cheque":
        # A cheque is confirmed only when it clears (docs/02 §6).
        raise AppError(422, "CHEQUE_NOT_CLEARED", "errors.chequeNotCleared")
    # Resident reports and bank transfers wait for the treasurer; cash and cheques are recorded.
    status = "pending" if by_resident or fields["method"] in ("upi", "neft") else "recorded"
    payment = Payment(
        society_id=society_id,
        status=status,
        reported_by_resident=by_resident,
        recorded_by=actor.id,
        **fields,
    )
    session.add(payment)
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="payment.report" if by_resident else "payment.record",
        entity_type="payment",
        entity_id=payment.id,
        after=_snap(payment),
    )
    if confirm_now:
        await confirm(session, society_id, actor, payment.id)
    await session.refresh(payment)
    return payment


async def confirm(
    session: AsyncSession, society_id: UUID, actor: User, payment_id: UUID
) -> Payment:
    """Money in: ledger entry, receipt and allocation in one transaction (docs/06 §4)."""
    payment = await get_payment(session, society_id, payment_id)
    if payment.status not in ("pending", "recorded"):
        raise AppError(409, "PAYMENT_NOT_OPEN", "errors.paymentNotOpen")
    society = await session.get(Society, society_id)
    if society is None:
        raise not_found()
    before = _snap(payment)
    payment.status = "confirmed"
    payment.confirmed_by = actor.id
    payment.confirmed_at = datetime.now(UTC)
    session.add(
        LedgerEntry(
            society_id=society_id,
            flat_id=payment.flat_id,
            entry_date=payment.received_on,
            entry_type="payment",
            amount_paise=-payment.amount_paise,
            source_type="payment",
            source_id=payment.id,
            created_by=actor.id,
        )
    )
    fy = financial_year(payment.received_on, society.financial_year_start_month)
    number = numbers.format_number(
        "receipt", fy, await numbers.reserve(session, society_id, "receipt", fy, 1)
    )
    session.add(
        Receipt(id=uuid4(), society_id=society_id, payment_id=payment.id, receipt_number=number)
    )
    await session.flush()
    await reconcile(session, society_id, payment.flat_id)
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="payment.confirm",
        entity_type="payment",
        entity_id=payment.id,
        before=before,
        after={**_snap(payment), "receipt_number": number},
    )
    await session.refresh(payment)
    return payment


async def bounce(
    session: AsyncSession, society_id: UUID, actor: User, payment_id: UUID, reason: str
) -> Payment:
    """A recorded cheque that did not clear. It never reached the ledger, so nothing to undo.
    Bounce charges only if configured (Q-004): none in v1."""
    payment = await get_payment(session, society_id, payment_id)
    if payment.method != "cheque" or payment.status != "recorded":
        raise AppError(409, "NOT_A_RECORDED_CHEQUE", "errors.notARecordedCheque")
    before = _snap(payment)
    payment.status = "bounced"
    payment.reason = reason
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="payment.bounce",
        entity_type="payment",
        entity_id=payment.id,
        before=before,
        after=_snap(payment),
        reason=reason,
    )
    return payment


async def reverse(
    session: AsyncSession, society_id: UUID, actor: User, payment_id: UUID, reason: str
) -> Payment:
    """Undo a payment with a reason (docs/06 §4). A confirmed payment gets a reversal row, a
    reversal ledger entry of +amount, its allocations undone and its receipt cancelled. A
    payment not yet confirmed is simply marked reversed."""
    payment = await get_payment(session, society_id, payment_id)
    if payment.status not in ("pending", "recorded", "confirmed"):
        raise AppError(409, "PAYMENT_NOT_REVERSIBLE", "errors.paymentNotReversible")
    before = _snap(payment)
    was_confirmed = payment.status == "confirmed"
    payment.status = "reversed"
    payment.reason = reason
    now = datetime.now(UTC)

    if was_confirmed:
        session.add(
            Payment(
                society_id=society_id,
                flat_id=payment.flat_id,
                amount_paise=payment.amount_paise,
                method=payment.method,
                status="reversed",
                received_on=payment.received_on,
                reference=payment.reference,
                reversal_of=payment.id,
                reason=reason,
                recorded_by=actor.id,
            )
        )
        entry = await session.scalar(
            select(LedgerEntry).where(
                LedgerEntry.source_type == "payment",
                LedgerEntry.source_id == payment.id,
                LedgerEntry.entry_type == "payment",
            )
        )
        session.add(
            LedgerEntry(
                society_id=society_id,
                flat_id=payment.flat_id,
                # Never dated before the payment it undoes.
                entry_date=max(today_ist(), payment.received_on),
                entry_type="reversal",
                amount_paise=payment.amount_paise,
                source_type="payment",
                source_id=payment.id,
                reverses_entry_id=entry.id if entry else None,
                reason=reason,
                created_by=actor.id,
            )
        )
        for allocation in await session.scalars(
            select(PaymentAllocation).where(
                PaymentAllocation.payment_id == payment.id, PaymentAllocation.reversed_at.is_(None)
            )
        ):
            allocation.reversed_at = now
        receipt = await session.scalar(select(Receipt).where(Receipt.payment_id == payment.id))
        if receipt:
            receipt.cancelled_at = now
            receipt.cancelled_reason = reason
        await session.flush()
        await reconcile(session, society_id, payment.flat_id)

    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="payment.reverse",
        entity_type="payment",
        entity_id=payment.id,
        before=before,
        after=_snap(payment),
        reason=reason,
    )
    return payment


async def list_payments(
    session: AsyncSession,
    society_id: UUID,
    status: str | None = None,
    flat_id: UUID | None = None,
) -> list[Payment]:
    # Reversal rows are bookkeeping; the list shows the original with status "reversed".
    query = select(Payment).where(Payment.society_id == society_id, Payment.reversal_of.is_(None))
    if status:
        query = query.where(Payment.status == status)
    if flat_id:
        query = query.where(Payment.flat_id == flat_id)
    return list(await session.scalars(query.order_by(Payment.created_at.desc()).limit(500)))


async def receipts_for(session: AsyncSession, payment_ids: list[UUID]) -> dict[UUID, Receipt]:
    if not payment_ids:
        return {}
    rows = await session.scalars(select(Receipt).where(Receipt.payment_id.in_(payment_ids)))
    return {r.payment_id: r for r in rows}


async def allocations_for(session: AsyncSession, payment_id: UUID) -> list[tuple[str, int]]:
    """(what it settled, amount) for active allocations: a bill number or 'opening'."""
    rows = await session.execute(
        select(Bill.bill_number, PaymentAllocation.amount_paise)
        .outerjoin(Bill, Bill.id == PaymentAllocation.bill_id)
        .where(PaymentAllocation.payment_id == payment_id, PaymentAllocation.reversed_at.is_(None))
        .order_by(PaymentAllocation.created_at)
    )
    return [(number or "opening", int(amount)) for number, amount in rows]


# --- dues and the flat ledger ---------------------------------------------------------


@dataclass
class FlatDues:
    flat_id: UUID
    balance_paise: int
    months_pending: int
    bucket: str


async def dues(session: AsyncSession, society_id: UUID) -> list[FlatDues]:
    flat_ids = list(
        await session.scalars(
            select(Flat.id).where(Flat.society_id == society_id, Flat.is_active.is_(True))
        )
    )
    balances = await ledger.balances(session, flat_ids)
    items = await open_items(session, flat_ids)
    result = []
    for fid in flat_ids:
        months = months_pending(items[fid])
        result.append(FlatDues(fid, balances[fid], months, bucket_for(months)))
    return sorted(result, key=lambda d: -d.balance_paise)


async def outstanding_total(session: AsyncSession, society_id: UUID) -> int:
    """What flats owe in total (advances not netted off), for the committee home."""
    return sum(max(d.balance_paise, 0) for d in await dues(session, society_id))


async def collected_between(session: AsyncSession, society_id: UUID, start: date, end: date) -> int:
    """Confirmed money received between two dates (inclusive), for the committee home."""
    total = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount_paise), 0)).where(
            Payment.society_id == society_id,
            Payment.status == "confirmed",
            Payment.received_on >= start,
            Payment.received_on <= end,
        )
    )
    return int(total or 0)


@dataclass
class LedgerLine:
    entry: LedgerEntry
    running_paise: int
    document: str | None


async def flat_ledger(session: AsyncSession, society_id: UUID, flat_id: UUID) -> list[LedgerLine]:
    flat = await session.get(Flat, flat_id)
    if flat is None or flat.society_id != society_id:
        raise not_found()
    entries = list(
        await session.scalars(
            select(LedgerEntry)
            .where(LedgerEntry.flat_id == flat_id)
            .order_by(LedgerEntry.entry_date, LedgerEntry.created_at)
        )
    )
    bill_ids = [e.source_id for e in entries if e.source_type == "bill" and e.source_id]
    payment_ids = [e.source_id for e in entries if e.source_type == "payment" and e.source_id]
    bill_numbers: dict[UUID, str] = {}
    if bill_ids:
        rows = await session.execute(select(Bill.id, Bill.bill_number).where(Bill.id.in_(bill_ids)))
        bill_numbers = {bid: number for bid, number in rows}
    receipts = await receipts_for(session, payment_ids)
    running = 0
    lines = []
    for entry in entries:
        running += entry.amount_paise
        document = None
        if entry.source_type == "bill" and entry.source_id:
            document = bill_numbers.get(entry.source_id)
        elif entry.source_type == "payment" and entry.source_id in receipts:
            document = receipts[entry.source_id].receipt_number
        lines.append(LedgerLine(entry, running, document))
    return lines
