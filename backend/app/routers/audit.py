"""Audit log viewer (docs/04 §14). Roles per docs/02 §2: admin, treasurer and auditor."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.deps import SessionDep, SocietyContext, require_role
from app.schemas.audit import AuditEntryOut, AuditPageOut
from app.services import audit as service

router = APIRouter(prefix="/societies/{society_id}", tags=["audit"])

Viewer = Annotated[SocietyContext, Depends(require_role("admin", "treasurer", "auditor"))]


@router.get("/audit-log")
async def audit_log(
    ctx: Viewer,
    session: SessionDep,
    entity_type: Annotated[str | None, Query(max_length=50)] = None,
    action: Annotated[str | None, Query(max_length=80)] = None,
    before_id: Annotated[int | None, Query(ge=1)] = None,
) -> AuditPageOut:
    page = await service.list_entries(
        session, ctx.society_id, entity_type=entity_type, action=action, before_id=before_id
    )
    return AuditPageOut(
        entries=[
            AuditEntryOut(
                id=r.id,
                created_at=r.created_at,
                actor_user_id=r.actor_user_id,
                actor_name=page.actors.get(r.actor_user_id) if r.actor_user_id else None,
                action=r.action,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                before=r.before,
                after=r.after,
                reason=r.reason,
            )
            for r in page.rows
        ],
        next_before_id=page.next_before_id,
    )
