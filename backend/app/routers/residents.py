"""The resident app's view of their own flats (docs/02 §11, docs/07 M7): dues, how to pay by
UPI, bills and receipts. Every route checks the person is linked to the flat; a tenant sees
amounts and pays only if the owner allowed it."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select

from app.deps import SessionDep, SocietyContext, require_role
from app.errors import not_found
from app.models import Bill, Payment, Society
from app.pdf import bills as pdf
from app.routers.billing import _render as render_bills
from app.routers.billing import _views as bill_views
from app.routers.payments import receipt_pdf_for
from app.schemas.billing import BillSummaryOut
from app.schemas.payments import PaymentOut
from app.services import billing as billing_service
from app.services import ledger, residents
from app.services import payments as payment_service

router = APIRouter(prefix="/societies/{society_id}/my/flats", tags=["resident"])

Member = Annotated[SocietyContext, Depends(require_role())]


class LatestBillOut(BaseModel):
    id: UUID
    bill_number: str
    total_due_paise: int
    due_date: date
    status: str


class PayInfoOut(BaseModel):
    amount_paise: int
    upi_id: str
    payee: str
    # upi://pay?... deep link; opens any UPI app with the amount filled in (docs/04 §8).
    upi_link: str
    qr_data_uri: str


class ResidentFlatOut(BaseModel):
    flat_id: UUID
    label: str
    role: str
    can_pay: bool
    # Amounts only when the person may see them (a tenant needs the owner's permission).
    balance_paise: int | None
    months_pending: int | None
    latest_bill: LatestBillOut | None
    pending_reports: int
    pay: PayInfoOut | None


@router.get("")
async def my_flats(ctx: Member, session: SessionDep) -> list[ResidentFlatOut]:
    access = await residents.my_flats(session, ctx.society_id, ctx.user)
    if not access:
        return []
    society = await session.get(Society, ctx.society_id)
    assert society is not None
    labels = await billing_service.flat_labels(session, ctx.society_id)
    flat_ids = [a.flat_id for a in access if a.can_pay]
    items = await payment_service.open_items(session, flat_ids)
    balances = await ledger.balances(session, flat_ids)
    out = []
    for a in access:
        latest = None
        pending = 0
        pay = None
        balance = months = None
        if a.can_pay:
            balance = balances[a.flat_id]
            months = payment_service.months_pending(items[a.flat_id])
            bill = await session.scalar(
                select(Bill)
                .where(Bill.flat_id == a.flat_id, Bill.status != "cancelled")
                .order_by(Bill.bill_date.desc(), Bill.bill_number.desc())
                .limit(1)
            )
            if bill:
                latest = LatestBillOut(
                    id=bill.id,
                    bill_number=bill.bill_number,
                    total_due_paise=bill.total_due_paise,
                    due_date=bill.due_date,
                    status=bill.status,
                )
            pending = (
                await session.scalar(
                    select(func.count(Payment.id)).where(
                        Payment.flat_id == a.flat_id, Payment.status.in_(("pending", "recorded"))
                    )
                )
                or 0
            )
            if society.upi_id and balance > 0:
                payee = society.upi_payee_name or society.name
                note = f"{labels.get(a.flat_id, '')} {latest.bill_number if latest else ''}".strip()
                link = pdf.upi_link(society.upi_id, payee, balance, note)
                pay = PayInfoOut(
                    amount_paise=balance,
                    upi_id=society.upi_id,
                    payee=payee,
                    upi_link=link,
                    qr_data_uri=pdf.qr_data_uri(link),
                )
        out.append(
            ResidentFlatOut(
                flat_id=a.flat_id,
                label=labels.get(a.flat_id, ""),
                role=a.role,
                can_pay=a.can_pay,
                balance_paise=balance,
                months_pending=months,
                latest_bill=latest,
                pending_reports=pending,
                pay=pay,
            )
        )
    return out


@router.get("/{flat_id}/bills")
async def my_bills(flat_id: UUID, ctx: Member, session: SessionDep) -> list[BillSummaryOut]:
    await residents.flat_access(session, ctx.society_id, ctx.user, flat_id, to_pay=True)
    labels = await billing_service.flat_labels(session, ctx.society_id)
    rows = await billing_service.list_bills(session, ctx.society_id, flat_id=flat_id)
    return [
        BillSummaryOut(
            id=b.id,
            flat_id=b.flat_id,
            flat_label=labels.get(b.flat_id, ""),
            bill_number=b.bill_number,
            member_name=b.member_name,
            charges_paise=b.charges_paise,
            arrears_paise=b.arrears_paise,
            advance_paise=b.advance_paise,
            interest_paise=b.interest_paise,
            total_due_paise=b.total_due_paise,
            status=b.status,
            replaces_bill_id=b.replaces_bill_id,
        )
        for b in rows
        if b.status != "cancelled"
    ]


@router.get("/{flat_id}/bills/{bill_id}/pdf", response_class=Response)
async def my_bill_pdf(flat_id: UUID, bill_id: UUID, ctx: Member, session: SessionDep) -> Response:
    await residents.flat_access(session, ctx.society_id, ctx.user, flat_id, to_pay=True)
    bill = await billing_service.get_bill(session, ctx.society_id, bill_id)
    if bill.flat_id != flat_id:
        raise not_found()
    society = await session.get(Society, ctx.society_id)
    assert society is not None
    content = render_bills(
        await bill_views(session, ctx.society_id, [bill]), society.default_language
    )
    filename = bill.bill_number.replace("/", "-") + ".pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/{flat_id}/payments")
async def my_payments(flat_id: UUID, ctx: Member, session: SessionDep) -> list[PaymentOut]:
    """Confirmed payments with receipts, and reports still waiting for the treasurer
    ("Received, waiting for confirmation", docs/02 §6)."""
    await residents.flat_access(session, ctx.society_id, ctx.user, flat_id, to_pay=True)
    rows = await payment_service.list_payments(session, ctx.society_id, flat_id=flat_id)
    receipts = await payment_service.receipts_for(session, [p.id for p in rows])
    out = []
    for p in rows:
        item = PaymentOut.model_validate(p)
        if p.id in receipts:
            item.receipt_number = receipts[p.id].receipt_number
            item.receipt_cancelled = receipts[p.id].cancelled_at is not None
        out.append(item)
    return out


@router.get("/{flat_id}/payments/{payment_id}/receipt", response_class=Response)
async def my_receipt(flat_id: UUID, payment_id: UUID, ctx: Member, session: SessionDep) -> Response:
    await residents.flat_access(session, ctx.society_id, ctx.user, flat_id, to_pay=True)
    payment = await payment_service.get_payment(session, ctx.society_id, payment_id)
    if payment.flat_id != flat_id:
        raise not_found()
    return await receipt_pdf_for(session, ctx.society_id, payment)
