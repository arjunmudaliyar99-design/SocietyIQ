"""Charge setup, per-flat extras and the preview (docs/02 §5). Manage: admin, treasurer,
consultant; view: committee and auditor (docs/02 §2). Society settings: admin only."""

from dataclasses import asdict
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import Response

from app.calc.legal import Problem
from app.config import get_settings
from app.deps import SessionDep, SocietyContext, require_role
from app.errors import AppError
from app.models import ImportJob
from app.schemas.charges import (
    ChargeHeadIn,
    ChargeHeadOut,
    ChargeHeadSaved,
    ChargeHeadUpdate,
    EndDateIn,
    ExcludedFlatOut,
    LegalProblemOut,
    OverrideIn,
    OverrideOut,
    ParkingIn,
    ParkingOut,
    PreviewFlatOut,
    PreviewHeadOut,
    PreviewOut,
    PropertyTaxIn,
    PropertyTaxOut,
    SettingsOut,
    SettingsUpdate,
    StandardHeadOut,
    TaxImportOut,
    TaxImportRowOut,
)
from app.schemas.flats import ImportIssueOut
from app.services import charges as service
from app.services import tax_import
from app.services.flats import MANAGE_ROLES, VIEW_ROLES
from app.services.societies import get_society
from app.services.workbook import XLSX_MIME

router = APIRouter(prefix="/societies/{society_id}", tags=["charges"])

Viewer = Annotated[SocietyContext, Depends(require_role(*VIEW_ROLES))]
Manager = Annotated[SocietyContext, Depends(require_role(*MANAGE_ROLES))]
Admin = Annotated[SocietyContext, Depends(require_role("admin"))]


@router.get("/settings")
async def read_settings(ctx: Viewer, session: SessionDep) -> SettingsOut:
    return SettingsOut.model_validate(await get_society(session, ctx.society_id))


@router.patch("/settings")
async def change_settings(body: SettingsUpdate, ctx: Admin, session: SessionDep) -> SettingsOut:
    society = await service.update_settings(
        session, ctx.society_id, ctx.user, body.model_dump(exclude_unset=True)
    )
    return SettingsOut.model_validate(society)


@router.get("/charges/standard-heads")
async def standard_heads(ctx: Viewer, session: SessionDep) -> list[StandardHeadOut]:
    return [StandardHeadOut.model_validate(h) for h in await service.standard_head_list(session)]


@router.get("/charges/heads")
async def list_heads(ctx: Viewer, session: SessionDep) -> list[ChargeHeadOut]:
    return [
        ChargeHeadOut.model_validate(h) for h in await service.list_heads(session, ctx.society_id)
    ]


def _saved(head: object, problems: list[Problem]) -> ChargeHeadSaved:
    return ChargeHeadSaved(
        head=ChargeHeadOut.model_validate(head),
        warnings=[LegalProblemOut(**asdict(p)) for p in problems],
    )


@router.post("/charges/heads", status_code=status.HTTP_201_CREATED)
async def create_head(body: ChargeHeadIn, ctx: Manager, session: SessionDep) -> ChargeHeadSaved:
    head, problems = await service.save_head(session, ctx.society_id, ctx.user, body.model_dump())
    return _saved(head, problems)


@router.patch("/charges/heads/{head_id}")
async def update_head(
    head_id: UUID, body: ChargeHeadUpdate, ctx: Manager, session: SessionDep
) -> ChargeHeadSaved:
    head, problems = await service.save_head(
        session, ctx.society_id, ctx.user, body.model_dump(exclude_unset=True), head_id
    )
    return _saved(head, problems)


@router.get("/charges/preview")
async def preview(
    ctx: Viewer,
    session: SessionDep,
    period_start: Annotated[date, Query(description="First day of the billing period")],
) -> PreviewOut:
    p = await service.preview(session, ctx.society_id, period_start)
    head_totals = {str(h.id): 0 for h in p.heads}
    flats: list[PreviewFlatOut] = []
    for fid, lines in p.result.by_flat.items():
        for hid, amount in lines.items():
            head_totals[hid] += amount
        charges = p.result.totals[fid]
        flats.append(
            PreviewFlatOut(
                flat_id=UUID(fid),
                label=p.flats[fid].label,
                lines=lines,
                charges_paise=charges,
                rounding_paise=p.rounding[fid],
                total_paise=charges + p.rounding[fid],
                overridden=p.result.overridden.get(fid, []),
                warnings=p.result.warnings.get(fid, []),
            )
        )
    return PreviewOut(
        period_start=p.period.start,
        period_end=p.period.end,
        heads=[
            PreviewHeadOut(id=h.id, name=h.name, total_paise=head_totals[str(h.id)])
            for h in p.heads
        ],
        flats=flats,
        excluded=[
            ExcludedFlatOut(flat_id=UUID(fid), label=p.flats[fid].label, reasons=reasons)
            for fid, reasons in p.result.excluded.items()
        ],
        total_paise=sum(f.total_paise for f in flats),
        missing=p.missing,
    )


@router.get("/flats/{flat_id}/overrides")
async def list_overrides(flat_id: UUID, ctx: Viewer, session: SessionDep) -> list[OverrideOut]:
    rows = await service.list_overrides(session, ctx.society_id, flat_id)
    return [OverrideOut.model_validate(r) for r in rows]


@router.post("/flats/{flat_id}/overrides", status_code=status.HTTP_201_CREATED)
async def create_override(
    flat_id: UUID, body: OverrideIn, ctx: Manager, session: SessionDep
) -> OverrideOut:
    row = await service.create_override(
        session, ctx.society_id, ctx.user, flat_id, body.model_dump()
    )
    return OverrideOut.model_validate(row)


@router.patch("/flats/{flat_id}/overrides/{override_id}")
async def end_override(
    flat_id: UUID, override_id: UUID, body: EndDateIn, ctx: Manager, session: SessionDep
) -> OverrideOut:
    row = await service.end_override(
        session, ctx.society_id, ctx.user, flat_id, override_id, body.end_date
    )
    return OverrideOut.model_validate(row)


@router.get("/flats/{flat_id}/parking")
async def list_parking(flat_id: UUID, ctx: Viewer, session: SessionDep) -> list[ParkingOut]:
    rows = await service.list_parking(session, ctx.society_id, flat_id)
    return [ParkingOut.model_validate(r) for r in rows]


@router.post("/flats/{flat_id}/parking", status_code=status.HTTP_201_CREATED)
async def create_parking(
    flat_id: UUID, body: ParkingIn, ctx: Manager, session: SessionDep
) -> ParkingOut:
    row = await service.create_parking(
        session, ctx.society_id, ctx.user, flat_id, body.model_dump()
    )
    return ParkingOut.model_validate(row)


@router.patch("/flats/{flat_id}/parking/{allotment_id}")
async def end_parking(
    flat_id: UUID, allotment_id: UUID, body: EndDateIn, ctx: Manager, session: SessionDep
) -> ParkingOut:
    row = await service.end_parking(
        session, ctx.society_id, ctx.user, flat_id, allotment_id, body.end_date
    )
    return ParkingOut.model_validate(row)


@router.get("/flats/{flat_id}/property-tax")
async def list_tax(flat_id: UUID, ctx: Viewer, session: SessionDep) -> list[PropertyTaxOut]:
    rows = await service.list_tax(session, ctx.society_id, flat_id)
    return [PropertyTaxOut.model_validate(r) for r in rows]


@router.post("/flats/{flat_id}/property-tax", status_code=status.HTTP_201_CREATED)
async def add_tax(
    flat_id: UUID, body: PropertyTaxIn, ctx: Manager, session: SessionDep
) -> PropertyTaxOut:
    row = await service.add_tax(session, ctx.society_id, ctx.user, flat_id, body.model_dump())
    return PropertyTaxOut.model_validate(row)


def _tax_job_out(job: ImportJob) -> TaxImportOut:
    return TaxImportOut(
        id=job.id,
        status=job.status,
        row_count=job.row_count,
        ok_count=job.ok_count,
        error_count=job.error_count,
        rows=[
            TaxImportRowOut(
                row=r["row"],
                status=r["status"],
                issues=[ImportIssueOut(**i) for i in r["issues"]],
                flat_label=r["data"]["flat_label"],
                financial_year=r["data"]["financial_year"],
                annual_amount_paise=r["data"]["annual_amount_paise"],
                is_exempt=r["data"]["is_exempt"],
            )
            for r in job.preview.get("rows", [])
        ],
    )


@router.get("/property-tax/template", response_class=Response)
async def tax_template(ctx: Manager) -> Response:
    return Response(
        content=tax_import.build_template(),
        media_type=XLSX_MIME,
        headers={"Content-Disposition": 'attachment; filename="societyiq-property-tax.xlsx"'},
    )


@router.post("/property-tax/imports", status_code=status.HTTP_201_CREATED)
async def tax_upload(
    file: Annotated[UploadFile, File()], ctx: Manager, session: SessionDep
) -> TaxImportOut:
    limit = get_settings().max_upload_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise AppError(413, "FILE_TOO_LARGE", "errors.fileTooLarge")
    job = await tax_import.preview(session, ctx.society_id, ctx.user, file.filename, data)
    return _tax_job_out(job)


@router.post("/property-tax/imports/{job_id}/confirm")
async def tax_confirm(job_id: UUID, ctx: Manager, session: SessionDep) -> TaxImportOut:
    return _tax_job_out(await tax_import.confirm(session, ctx.society_id, ctx.user, job_id))
