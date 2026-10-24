"""The signed-in user: profile, preferences, consent, societies (docs/02 §3)."""

from fastapi import APIRouter

from app.config import get_settings
from app.deps import CurrentUserDep, SessionDep
from app.models import Consent
from app.schemas.auth import ConsentIn, ConsentOut, ConsentStatusOut, MeOut, PreferencesIn
from app.schemas.societies import MySocietyOut
from app.services import auth as service
from app.services import societies as society_service

router = APIRouter(prefix="/me", tags=["me"])


async def _me(session: SessionDep, user: CurrentUserDep) -> MeOut:
    consents = await service.current_consents(session, user)
    out = MeOut.model_validate(user)
    out.needs_consent = service.needs_consent(consents)
    return out


def _consent_status(consents: list[Consent]) -> ConsentStatusOut:
    return ConsentStatusOut(
        policy_version=get_settings().policy_version,
        needs_consent=service.needs_consent(consents),
        granted=[ConsentOut.model_validate(c) for c in consents],
    )


@router.get("")
async def get_me(session: SessionDep, user: CurrentUserDep) -> MeOut:
    return await _me(session, user)


@router.patch("/preferences")
async def update_preferences(
    body: PreferencesIn, session: SessionDep, user: CurrentUserDep
) -> MeOut:
    await service.update_preferences(session, user, body.model_dump(exclude_none=True))
    return await _me(session, user)


@router.get("/consents")
async def get_consents(session: SessionDep, user: CurrentUserDep) -> ConsentStatusOut:
    return _consent_status(await service.current_consents(session, user))


@router.post("/consents")
async def give_consents(
    body: ConsentIn, session: SessionDep, user: CurrentUserDep
) -> ConsentStatusOut:
    consents = await service.record_consents(session, user, body.analytics, body.notifications)
    return _consent_status(consents)


@router.get("/societies")
async def my_societies(session: SessionDep, user: CurrentUserDep) -> list[MySocietyOut]:
    rows = await society_service.list_my_societies(session, user)
    return [
        MySocietyOut(id=r.society.id, name=r.society.name, city=r.society.city, roles=r.roles)
        for r in rows
    ]
