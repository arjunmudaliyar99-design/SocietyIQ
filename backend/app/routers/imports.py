"""Flats and members import from Excel (docs/02 §4): template, upload with preview, confirm."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import Response

from app.config import get_settings
from app.deps import SessionDep, SocietyContext, require_role
from app.errors import AppError
from app.models import ImportJob
from app.schemas.flats import ImportIssueOut, ImportJobOut, ImportRowOut
from app.services import imports as service
from app.services.flats import MANAGE_ROLES

router = APIRouter(prefix="/societies/{society_id}/imports", tags=["imports"])

Manager = Annotated[SocietyContext, Depends(require_role(*MANAGE_ROLES))]


def _job_out(job: ImportJob) -> ImportJobOut:
    rows = [
        ImportRowOut(
            row=r["row"],
            status=r["status"],
            issues=[ImportIssueOut(**i) for i in r["issues"]],
            wing=r["data"].get("wing"),
            flat_number=r["data"].get("flat_number"),
            owner_name=r["data"].get("owner_name"),
            opening_balance_paise=r["data"].get("opening_balance_paise"),
        )
        for r in job.preview.get("rows", [])
    ]
    return ImportJobOut(
        id=job.id,
        status=job.status,
        row_count=job.row_count,
        ok_count=job.ok_count,
        error_count=job.error_count,
        rows=rows,
    )


@router.get("/template", response_class=Response)
async def download_template(ctx: Manager) -> Response:
    return Response(
        content=service.build_template(),
        media_type=service.XLSX_MIME,
        headers={"Content-Disposition": 'attachment; filename="societyiq-flats-template.xlsx"'},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload(
    file: Annotated[UploadFile, File()], ctx: Manager, session: SessionDep
) -> ImportJobOut:
    limit = get_settings().max_upload_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise AppError(413, "FILE_TOO_LARGE", "errors.fileTooLarge")
    job = await service.preview(session, ctx.society_id, ctx.user, file.filename, data)
    return _job_out(job)


@router.get("/{job_id}")
async def get_job(job_id: UUID, ctx: Manager, session: SessionDep) -> ImportJobOut:
    return _job_out(await service.get_job(session, ctx.society_id, job_id))


@router.post("/{job_id}/confirm")
async def confirm(job_id: UUID, ctx: Manager, session: SessionDep) -> ImportJobOut:
    return _job_out(await service.confirm(session, ctx.society_id, ctx.user, job_id))
