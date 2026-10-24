"""Scheduled-job endpoints (docs/04 §13), called by GitHub Actions with a shared token.
Not tied to a user or a society; protected by INTERNAL_JOBS_TOKEN only."""

import hmac
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Header
from pydantic import BaseModel

from app.config import get_settings
from app.errors import AppError
from app.jobs.billing import create_draft_billing_runs
from app.timeutil import today_ist

router = APIRouter(prefix="/internal/jobs", tags=["internal"])


def _check_token(token: str | None) -> None:
    expected = get_settings().internal_jobs_token
    if not expected or not token or not hmac.compare_digest(token, expected):
        raise AppError(401, "UNAUTHORIZED", "errors.signInAgain")


class JobIn(BaseModel):
    # Lets tests and a manual re-run pick the day; refused in production.
    today: date | None = None


@router.post("/create-draft-billing-runs")
async def run_billing_job(
    body: JobIn, x_jobs_token: Annotated[str | None, Header()] = None
) -> dict[str, Any]:
    _check_token(x_jobs_token)
    if body.today and get_settings().app_env == "production":
        raise AppError(422, "TODAY_NOT_ALLOWED", "errors.generic")
    report = await create_draft_billing_runs(body.today or today_ist())
    return report.as_dict()
