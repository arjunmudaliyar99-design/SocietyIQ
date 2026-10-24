"""Property tax from Excel (docs/02 §5 task 6): template → preview → confirm. Only error-free
rows are saved; each becomes a new assessment row (append-only, newest wins)."""

from dataclasses import asdict
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.errors import AppError, not_found
from app.models import Attachment, Flat, ImportJob, PropertyTaxAssessment, User, Wing
from app.services import audit, workbook
from app.services.societies import DEFAULT_WING_NAME
from app.services.tax_rows import TAX_COLUMNS, check_tax_rows
from app.services.workbook import XLSX_MIME
from app.storage import store

SHEET_NAME = "Property tax"
INSTRUCTIONS = [
    "How to fill the Property tax sheet",
    "One row per flat per financial year. Copy the amounts from the municipal bill.",
    "SocietyIQ never calculates municipal tax; it passes on what the authority fixed.",
    "Wing and Flat number: exactly as in SocietyIQ. Leave Wing empty if there are no wings.",
    "Municipal authority: for example MCGM or TMC.",
    "Financial year: for example 2026-27.",
    "Annual property tax: the yearly amount for the flat, in rupees.",
    "Exempt: Y if the bill shows the flat as exempt; then leave the amount empty and give "
    "the reason, for example MCGM residential up to 500 sq ft carpet.",
    "Nothing is saved until you check the preview and confirm.",
]


def build_template() -> bytes:
    return workbook.build_template(SHEET_NAME, TAX_COLUMNS, {"is_exempt": "Y,N"}, INSTRUCTIONS)


async def _flat_map(
    session: AsyncSession, society_id: UUID
) -> tuple[dict[tuple[str, str], str], str]:
    rows = await session.execute(
        select(Wing.name, Flat.flat_number, Flat.id)
        .join(Flat, Flat.wing_id == Wing.id)
        .where(Flat.society_id == society_id)
    )
    flats = {(w.lower(), n.lower()): str(fid) for w, n, fid in rows}
    wings = list(await session.scalars(select(Wing.name).where(Wing.society_id == society_id)))
    blank = wings[0] if len(wings) == 1 else DEFAULT_WING_NAME
    return flats, blank.lower()


def _row_json(r: Any) -> dict[str, Any]:  # noqa: ANN401
    return {
        "row": r.row,
        "status": r.status,
        "issues": [asdict(i) for i in r.issues],
        "data": r.data,
    }


async def preview(
    session: AsyncSession, society_id: UUID, actor: User, filename: str | None, data: bytes
) -> ImportJob:
    if len(data) > get_settings().max_upload_bytes:
        raise AppError(413, "FILE_TOO_LARGE", "errors.fileTooLarge")
    raw = workbook.read_workbook(data, SHEET_NAME, TAX_COLUMNS, "flat_number")
    stored = await store(society_id, "imports", "xlsx", data, XLSX_MIME)
    job_id = uuid4()
    session.add(
        attachment := Attachment(
            society_id=society_id,
            owner_type="import_job",
            owner_id=job_id,
            storage_path=stored.path,
            mime=XLSX_MIME,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            original_filename=(filename or "")[:200] or None,
            uploaded_by=actor.id,
        )
    )
    await session.flush()
    flats, blank = await _flat_map(session, society_id)
    results = check_tax_rows(raw, flats, blank)
    ok = sum(1 for r in results if r.status == "ok")
    job = ImportJob(
        id=job_id,
        society_id=society_id,
        kind="property_tax",
        attachment_id=attachment.id,
        status="previewed",
        row_count=len(results),
        ok_count=ok,
        error_count=len(results) - ok,
        preview={"rows": [_row_json(r) for r in results]},
        created_by=actor.id,
    )
    session.add(job)
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="import.preview",
        entity_type="import_job",
        entity_id=job.id,
        after={
            "kind": "property_tax",
            "rows": len(results),
            "ok": ok,
            "file_sha256": stored.sha256,
        },
    )
    await session.refresh(job)
    return job


async def confirm(session: AsyncSession, society_id: UUID, actor: User, job_id: UUID) -> ImportJob:
    job = await session.get(ImportJob, job_id)
    if job is None or job.society_id != society_id or job.kind != "property_tax":
        raise not_found()
    if job.status != "previewed":
        raise AppError(409, "IMPORT_DONE", "errors.importDone")
    saved = 0
    for row in job.preview["rows"]:
        if row["status"] != "ok":
            continue
        data = row["data"]
        if await session.get(Flat, UUID(data["flat_id"])) is None:
            continue
        tax = PropertyTaxAssessment(
            society_id=society_id,
            flat_id=UUID(data["flat_id"]),
            authority=data["authority"],
            financial_year=data["financial_year"],
            annual_amount_paise=data["annual_amount_paise"],
            is_exempt=data["is_exempt"],
            exemption_reason=data["exemption_reason"],
            source_document_id=job.attachment_id,
            entered_by=actor.id,
        )
        session.add(tax)
        await session.flush()
        await audit.record(
            session,
            society_id=society_id,
            actor_user_id=actor.id,
            action="property_tax.import",
            entity_type="property_tax_assessment",
            entity_id=tax.id,
            after={"import_job_id": str(job.id), "row": row["row"], **data},
        )
        saved += 1
    job.status = "imported"
    job.ok_count = saved
    job.error_count = job.row_count - saved
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="import.confirm",
        entity_type="import_job",
        entity_id=job.id,
        after={"kind": "property_tax", "imported": saved, "skipped": job.error_count},
    )
    await session.refresh(job)
    return job
