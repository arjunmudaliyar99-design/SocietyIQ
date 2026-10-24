"""Export all society data (docs/07 M11). Roles per docs/02 §2: admin, treasurer, auditor.
Each export is written to the audit log, since it hands over members' personal data."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.config import get_settings
from app.deps import SessionDep, SocietyContext, require_role
from app.errors import AppError, not_found
from app.models import Society
from app.pdf import bills as pdf
from app.schemas.exports import ExportFormat
from app.services import exports as service
from app.timeutil import today_ist

router = APIRouter(prefix="/societies/{society_id}", tags=["exports"])

Exporter = Annotated[SocietyContext, Depends(require_role("admin", "treasurer", "auditor"))]

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/export", response_class=Response)
async def export_society(
    ctx: Exporter,
    session: SessionDep,
    file_format: Annotated[ExportFormat, Query(alias="format")] = "xlsx",
) -> Response:
    society = await session.get(Society, ctx.society_id)
    if society is None:
        raise not_found()
    sheets = await service.collect(session, ctx.society_id)
    name = f"societyiq-export-{today_ist():%Y-%m-%d}"
    if file_format == "xlsx":
        content, media = service.to_xlsx(sheets), XLSX
    else:
        html = pdf.render_template(
            "export.html",
            "en",
            get_settings().company_legal_name,
            society_name=society.name,
            as_on=today_ist().strftime("%d %b %Y"),
            sheets=sheets,
            text=service.as_text,
        )
        try:
            content, media = pdf.render_pdf(html), "application/pdf"
        except pdf.PdfUnavailable as exc:
            raise AppError(503, "PDF_UNAVAILABLE", "errors.pdfUnavailable") from exc
    await service.record_export(session, ctx.society_id, ctx.user, file_format, sheets)
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{name}.{file_format}"'},
    )
