"""Payments, receipts, dues and the flat ledger (docs/02 §6-7).

Roles (docs/02 §2): admin, treasurer and consultant record, confirm and reverse payments;
the auditor views them. Dues and ledgers: also the committee. Residents report their own
payments ("I have paid") for a flat they are linked to.
"""

from collections import Counter
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy import select

from app.config import get_settings
from app.deps import SessionDep, SocietyContext, require_role
from app.errors import AppError
from app.models import ChargeHead, Member, Payment, Receipt, Society
from app.pdf import bills as pdf
from app.pdf import documents
from app.schemas.payments import (
    AllocationOut,
    DuesOut,
    DuesRowOut,
    FlatLedgerOut,
    LedgerLineOut,
    PaymentDetailOut,
    PaymentIn,
    PaymentOut,
    ReasonIn,
    ResidentPaymentIn,
)
from app.services import billing as billing_service
from app.services import payments as service
from app.services import residents
from app.timeutil import today_ist

router = APIRouter(prefix="/societies/{society_id}", tags=["payments"])

MONEY_ROLES = ("admin", "treasurer", "consultant")
Recorder = Annotated[SocietyContext, Depends(require_role(*MONEY_ROLES))]
PaymentViewer = Annotated[SocietyContext, Depends(require_role(*MONEY_ROLES, "auditor"))]
DuesViewer = Annotated[SocietyContext, Depends(require_role(*MONEY_ROLES, "committee", "auditor"))]
AnyMember = Annotated[SocietyContext, Depends(require_role())]


async def _payment_out(
    session: SessionDep, society_id: UUID, rows: list[Payment]
) -> list[PaymentOut]:
    labels = await billing_service.flat_labels(session, society_id)
    receipts = await service.receipts_for(session, [p.id for p in rows])
    out = []
    for p in rows:
        item = PaymentOut.model_validate(p)
        item.flat_label = labels.get(p.flat_id, "")
        if p.id in receipts:
            item.receipt_number = receipts[p.id].receipt_number
            item.receipt_cancelled = receipts[p.id].cancelled_at is not None
        out.append(item)
    return out


async def _detail(session: SessionDep, society_id: UUID, payment: Payment) -> PaymentDetailOut:
    [base] = await _payment_out(session, society_id, [payment])
    allocations = await service.allocations_for(session, payment.id)
    return PaymentDetailOut(
        **base.model_dump(),
        allocations=[AllocationOut(settles=s, amount_paise=a) for s, a in allocations],
    )


@router.get("/payments")
async def list_payments(
    ctx: PaymentViewer,
    session: SessionDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    flat_id: Annotated[UUID | None, Query()] = None,
) -> list[PaymentOut]:
    rows = await service.list_payments(session, ctx.society_id, status_filter, flat_id)
    return await _payment_out(session, ctx.society_id, rows)


@router.post("/payments", status_code=status.HTTP_201_CREATED)
async def record_payment(body: PaymentIn, ctx: Recorder, session: SessionDep) -> PaymentDetailOut:
    fields = body.model_dump(exclude={"confirm_now"})
    payment = await service.record(
        session, ctx.society_id, ctx.user, fields, confirm_now=body.confirm_now
    )
    return await _detail(session, ctx.society_id, payment)


@router.get("/payments/{payment_id}")
async def get_payment(
    payment_id: UUID, ctx: PaymentViewer, session: SessionDep
) -> PaymentDetailOut:
    payment = await service.get_payment(session, ctx.society_id, payment_id)
    return await _detail(session, ctx.society_id, payment)


@router.post("/payments/{payment_id}/confirm")
async def confirm_payment(payment_id: UUID, ctx: Recorder, session: SessionDep) -> PaymentDetailOut:
    payment = await service.confirm(session, ctx.society_id, ctx.user, payment_id)
    return await _detail(session, ctx.society_id, payment)


@router.post("/payments/{payment_id}/bounce")
async def bounce_payment(
    payment_id: UUID, body: ReasonIn, ctx: Recorder, session: SessionDep
) -> PaymentDetailOut:
    payment = await service.bounce(session, ctx.society_id, ctx.user, payment_id, body.reason)
    return await _detail(session, ctx.society_id, payment)


@router.post("/payments/{payment_id}/reverse")
async def reverse_payment(
    payment_id: UUID, body: ReasonIn, ctx: Recorder, session: SessionDep
) -> PaymentDetailOut:
    payment = await service.reverse(session, ctx.society_id, ctx.user, payment_id, body.reason)
    return await _detail(session, ctx.society_id, payment)


async def _member_name(session: SessionDep, flat_id: UUID) -> str | None:
    return await session.scalar(
        select(Member.full_name)
        .where(Member.flat_id == flat_id, Member.to_date.is_(None))
        .order_by(Member.is_primary.desc(), Member.created_at)
        .limit(1)
    )


def _render(html: str) -> bytes:
    try:
        return pdf.render_pdf(html)
    except pdf.PdfUnavailable as exc:
        raise AppError(503, "PDF_UNAVAILABLE", "errors.pdfUnavailable") from exc


async def receipt_pdf_for(session: SessionDep, society_id: UUID, payment: Payment) -> Response:
    receipt = await session.scalar(select(Receipt).where(Receipt.payment_id == payment.id))
    if receipt is None:
        # No receipt exists until a payment is confirmed (docs/02 §6).
        raise AppError(409, "NO_RECEIPT", "errors.noReceipt")
    society = await session.get(Society, society_id)
    assert society is not None
    labels = await billing_service.flat_labels(session, society_id)
    view = documents.receipt_view(
        society=society,
        payment=payment,
        receipt=receipt,
        flat_label=labels.get(payment.flat_id, ""),
        member=await _member_name(session, payment.flat_id),
        allocations=await service.allocations_for(session, payment.id),
    )
    html = pdf.render_template(
        "receipts.html",
        society.default_language,
        get_settings().company_legal_name,
        receipts=[view],
    )
    filename = receipt.receipt_number.replace("/", "-") + ".pdf"
    return Response(
        content=_render(html),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/payments/{payment_id}/receipt", response_class=Response)
async def receipt_pdf(payment_id: UUID, ctx: PaymentViewer, session: SessionDep) -> Response:
    payment = await service.get_payment(session, ctx.society_id, payment_id)
    return await receipt_pdf_for(session, ctx.society_id, payment)


@router.get("/dues")
async def dues(
    ctx: DuesViewer,
    session: SessionDep,
    bucket: Annotated[str | None, Query()] = None,
) -> DuesOut:
    labels = await billing_service.flat_labels(session, ctx.society_id)
    all_rows = await service.dues(session, ctx.society_id)
    counts = Counter(r.bucket for r in all_rows)
    owing = [r for r in all_rows if r.balance_paise > 0 or r.months_pending > 0]
    shown = [r for r in owing if not bucket or r.bucket == bucket]
    return DuesOut(
        rows=[
            DuesRowOut(
                flat_id=r.flat_id,
                flat_label=labels.get(r.flat_id, ""),
                balance_paise=r.balance_paise,
                months_pending=r.months_pending,
                bucket=r.bucket,  # type: ignore[arg-type]
            )
            for r in shown
        ],
        counts={k: counts.get(k, 0) for k in ("paid_up", "friendly", "formal", "long")},
        outstanding_paise=sum(max(r.balance_paise, 0) for r in all_rows),
    )


async def _ledger(session: SessionDep, society_id: UUID, flat_id: UUID) -> FlatLedgerOut:
    lines = await service.flat_ledger(session, society_id, flat_id)
    labels = await billing_service.flat_labels(session, society_id)
    items = (await service.open_items(session, [flat_id]))[flat_id]
    return FlatLedgerOut(
        flat_id=flat_id,
        flat_label=labels.get(flat_id, ""),
        balance_paise=lines[-1].running_paise if lines else 0,
        months_pending=service.months_pending(items),
        lines=[
            LedgerLineOut(
                id=line.entry.id,
                entry_date=line.entry.entry_date,
                entry_type=line.entry.entry_type,  # type: ignore[arg-type]
                amount_paise=line.entry.amount_paise,
                running_paise=line.running_paise,
                document=line.document,
                reason=line.entry.reason,
            )
            for line in lines
        ],
    )


@router.get("/flats/{flat_id}/ledger")
async def flat_ledger(flat_id: UUID, ctx: DuesViewer, session: SessionDep) -> FlatLedgerOut:
    return await _ledger(session, ctx.society_id, flat_id)


@router.get("/flats/{flat_id}/ledger/export", response_class=Response)
async def export_ledger(
    flat_id: UUID,
    ctx: DuesViewer,
    session: SessionDep,
    file_format: Annotated[str, Query(alias="format", pattern="^(pdf|xlsx)$")] = "pdf",
) -> Response:
    """The flat's statement for a recovery application (docs/06 §6): every bill, payment,
    interest line and reversal, with the resolutions behind the charges."""
    society = await session.get(Society, ctx.society_id)
    assert society is not None
    lines = await service.flat_ledger(session, ctx.society_id, flat_id)
    labels = await billing_service.flat_labels(session, ctx.society_id)
    heads = list(
        await session.scalars(
            select(ChargeHead)
            .where(ChargeHead.society_id == ctx.society_id)
            .order_by(ChargeHead.sort_order, ChargeHead.name)
        )
    )
    view = documents.ledger_view(
        society=society,
        flat_label=labels.get(flat_id, ""),
        member=await _member_name(session, flat_id),
        lines=lines,
        heads=heads,
        as_on=today_ist(),
    )
    name = f"ledger-{view.flat}-{today_ist():%Y-%m-%d}"
    if file_format == "xlsx":
        return Response(
            content=documents.ledger_xlsx(view, lines),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{name}.xlsx"'},
        )
    html = pdf.render_template(
        "ledger.html", society.default_language, get_settings().company_legal_name, l=view
    )
    return Response(
        content=_render(html),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{name}.pdf"'},
    )


# --- residents ------------------------------------------------------------------------


@router.post("/flats/{flat_id}/payment-reports", status_code=status.HTTP_201_CREATED)
async def report_payment(
    flat_id: UUID, body: ResidentPaymentIn, ctx: AnyMember, session: SessionDep
) -> PaymentOut:
    await residents.flat_access(session, ctx.society_id, ctx.user, flat_id, to_pay=True)
    payment = await service.record(
        session,
        ctx.society_id,
        ctx.user,
        {"flat_id": flat_id, **body.model_dump()},
        by_resident=True,
    )
    [out] = await _payment_out(session, ctx.society_id, [payment])
    return out
