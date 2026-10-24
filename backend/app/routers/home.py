"""Committee home (docs/02 §10). Any committee-side role may view it."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps import SessionDep, SocietyContext, require_role
from app.schemas.home import AttentionOut, HomeOut, LatestRunOut
from app.services import home as service
from app.services.compliance import VIEW_ROLES
from app.timeutil import today_ist

router = APIRouter(prefix="/societies/{society_id}", tags=["home"])

Viewer = Annotated[SocietyContext, Depends(require_role(*VIEW_ROLES))]


@router.get("/home")
async def get_home(ctx: Viewer, session: SessionDep) -> HomeOut:
    h = await service.home(session, ctx.society_id, today_ist())
    run = h.latest_run
    return HomeOut(
        coming_soon=list(h.coming_soon),  # type: ignore[arg-type]
        open_complaints=h.open_complaints,
        compliance_overdue=h.compliance_overdue,
        compliance_due_soon=h.compliance_due_soon,
        next_bill_date=h.next_bill_date,
        latest_run=(
            LatestRunOut(id=run.id, period_start=run.period_start, status=run.status)  # type: ignore[arg-type]
            if run
            else None
        ),
        attention=[AttentionOut(**a) for a in h.attention],
    )
