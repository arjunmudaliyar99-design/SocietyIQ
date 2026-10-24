"""Billing runs and bills (docs/02 §5). Roles per docs/02 §2: admin and treasurer create and
approve; the consultant may create drafts only; committee and auditor view."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy import select

from app.config import get_settings
from app.deps import SessionDep, SocietyContext, require_role
from app.errors import AppError
from app.models import Bill
from app.pdf import bills as pdf
from app.schemas.billing import (
    BillLineOut,
    BillOut,
    BillSummaryOut,
    DraftFlatOut,
    ReasonIn,
    RunCreateIn,
    RunDetailOut,
    RunOut,
    warnings_out,
)
from app.services import billing as service
from app.services.flats import VIEW_ROLES
from app.storage import get_storage, store

router = APIRouter(prefix="/societies/{society_id}", tags=["billing"])

Viewer = Annotated[SocietyContext, Depends(require_role(*VIEW_ROLES))]
Creator = Annotated[SocietyContext, Depends(require_role("admin", "treasurer", "consultant"))]
Approver = Annotated[SocietyContext, Depends(require_role("admin", "treasurer"))]


def _summary(bill: Bill, labels: dict[UUID, str]) -> BillSummaryOut:
    return BillSummaryOut(
        id=bill.id,
        flat_id=bill.flat_id,
        flat_label=labels.get(bill.flat_id, ""),
        bill_number=bill.bill_number,
        member_name=bill.member_name,
        charges_paise=bill.charges_paise,
        arrears_paise=bill.arrears_paise,
        advance_paise=bill.advance_paise,
        interest_paise=bill.interest_paise,
        total_due_paise=bill.total_due_paise,
        status=bill.status,
        replaces_bill_id=bill.replaces_bill_id,
    )


def _run_fields(run: object) -> dict[str, object]:
    fields = {k: getattr(run, k) for k in RunOut.model_fields if k != "warnings"}
    fields["warnings"] = warnings_out(run.warnings)
    return fields


@router.get("/billing-runs")
async def list_runs(ctx: Viewer, session: SessionDep) -> list[RunOut]:
    return [RunOut(**_run_fields(r)) for r in await service.list_runs(session, ctx.society_id)]


@router.post("/billing-runs", status_code=status.HTTP_201_CREATED)
async def create_run(body: RunCreateIn, ctx: Creator, session: SessionDep) -> RunOut:
    run = await service.create_draft(session, ctx.society_id, ctx.user, body.period_start)
    return RunOut(**_run_fields(run))


@router.get("/billing-runs/{run_id}")
async def get_run(run_id: UUID, ctx: Viewer, session: SessionDep) -> RunDetailOut:
    run = await service.get_run(session, ctx.society_id, run_id)
    labels = await service.flat_labels(session, ctx.society_id)
    bills = await service.list_bills(session, ctx.society_id, run_id=run.id)
    draft = (
        [
            DraftFlatOut(flat_id=UUID(f["flat_id"]), label=f["label"], charges_paise=f["charges"])
            for f in run.charges_snapshot.get("flats", [])
        ]
        if run.status == "draft"
        else []
    )
    return RunDetailOut(
        **_run_fields(run),
        draft_flats=draft,
        bills=sorted((_summary(b, labels) for b in bills), key=lambda b: b.bill_number),
    )


@router.post("/billing-runs/{run_id}/approve")
async def approve_run(run_id: UUID, ctx: Approver, session: SessionDep) -> RunOut:
    run = await service.approve(session, ctx.society_id, ctx.user, run_id)
    return RunOut(**_run_fields(run))


@router.post("/billing-runs/{run_id}/cancel")
async def cancel_run(run_id: UUID, body: ReasonIn, ctx: Approver, session: SessionDep) -> RunOut:
    run = await service.cancel_draft(session, ctx.society_id, ctx.user, run_id, body.reason)
    return RunOut(**_run_fields(run))


@router.get("/bills")
async def list_bills(
    ctx: Viewer, session: SessionDep, flat_id: Annotated[UUID | None, Query()] = None
) -> list[BillSummaryOut]:
    labels = await service.flat_labels(session, ctx.society_id)
    rows = await service.list_bills(session, ctx.society_id, flat_id=flat_id)
    return [_summary(b, labels) for b in rows]


@router.get("/bills/{bill_id}")
async def get_bill(bill_id: UUID, ctx: Viewer, session: SessionDep) -> BillOut:
    bill = await service.get_bill(session, ctx.society_id, bill_id)
    labels = await service.flat_labels(session, ctx.society_id)
    lines = await service.bill_lines(session, bill.id)
    replaced_by = await session.scalar(select(Bill.id).where(Bill.replaces_bill_id == bill.id))
    return BillOut(
        **_summary(bill, labels).model_dump(),
        billing_run_id=bill.billing_run_id,
        period_start=bill.period_start,
        period_end=bill.period_end,
        bill_date=bill.bill_date,
        due_date=bill.due_date,
        cancelled_reason=bill.cancelled_reason,
        cancelled_at=bill.cancelled_at,
        lines=[BillLineOut.model_validate(line) for line in lines],
        replaced_by_bill_id=replaced_by,
    )


@router.post("/bills/{bill_id}/cancel")
async def cancel_bill(
    bill_id: UUID, body: ReasonIn, ctx: Approver, session: SessionDep
) -> BillSummaryOut:
    bill = await service.cancel_bill(session, ctx.society_id, ctx.user, bill_id, body.reason)
    return _summary(bill, await service.flat_labels(session, ctx.society_id))


@router.post("/bills/{bill_id}/reissue", status_code=status.HTTP_201_CREATED)
async def reissue_bill(bill_id: UUID, ctx: Approver, session: SessionDep) -> BillSummaryOut:
    bill = await service.reissue_bill(session, ctx.society_id, ctx.user, bill_id)
    return _summary(bill, await service.flat_labels(session, ctx.society_id))


async def _views(session: SessionDep, society_id: UUID, bills: list[Bill]) -> list[pdf.BillView]:
    society = await service.get_society_or_404(session, society_id)
    labels = await service.flat_labels(session, society_id)
    numbers = {b.id: b.bill_number for b in await service.list_bills(session, society_id)}
    return [
        pdf.bill_view(
            society=society,
            bill=b,
            lines=await service.bill_lines(session, b.id),
            flat_label=labels.get(b.flat_id, ""),
            replaces_number=numbers.get(b.replaces_bill_id) if b.replaces_bill_id else None,
        )
        for b in bills
    ]


def _pdf_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


def _render(views: list[pdf.BillView], language: str) -> bytes:
    try:
        return pdf.render_pdf(pdf.render_html(views, language, get_settings().company_legal_name))
    except pdf.PdfUnavailable as exc:
        raise AppError(503, "PDF_UNAVAILABLE", "errors.pdfUnavailable") from exc


@router.get("/bills/{bill_id}/pdf", response_class=Response)
async def bill_pdf(bill_id: UUID, ctx: Viewer, session: SessionDep) -> Response:
    """Rendered once and kept in storage (docs/04 §8); a cancelled bill is shown fresh with
    its CANCELLED mark."""
    bill = await service.get_bill(session, ctx.society_id, bill_id)
    filename = bill.bill_number.replace("/", "-") + ".pdf"
    if bill.pdf_path and bill.status != "cancelled":
        return _pdf_response(await get_storage().get(bill.pdf_path), filename)
    society = await service.get_society_or_404(session, ctx.society_id)
    content = _render(await _views(session, ctx.society_id, [bill]), society.default_language)
    if bill.status != "cancelled":
        stored = await store(ctx.society_id, "bills", "pdf", content, "application/pdf")
        bill.pdf_path = stored.path
        await session.flush()
    return _pdf_response(content, filename)


@router.get("/billing-runs/{run_id}/pdf", response_class=Response)
async def run_pdf(run_id: UUID, ctx: Viewer, session: SessionDep) -> Response:
    """Every live bill of the run, one per page, for the watchman to hand out."""
    run = await service.get_run(session, ctx.society_id, run_id)
    bills = [
        b
        for b in sorted(
            await service.list_bills(session, ctx.society_id, run_id=run.id),
            key=lambda b: b.bill_number,
        )
        if b.status != "cancelled"
    ]
    if not bills:
        raise AppError(409, "NO_BILLS", "errors.noBills")
    society = await service.get_society_or_404(session, ctx.society_id)
    content = _render(await _views(session, ctx.society_id, bills), society.default_language)
    return _pdf_response(content, f"bills-{run.period_start:%Y-%m}.pdf")
