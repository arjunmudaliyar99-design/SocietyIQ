"""Signed-in user, preferences and consent (docs/02 §3, docs/05 §1, docs/08 §8)."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthUser
from app.config import get_settings
from app.models import Consent, User
from app.services import audit

REQUIRED_CONSENTS = ("terms", "privacy")
OPTIONAL_CONSENTS = ("analytics", "notifications")


async def ensure_user(session: AsyncSession, auth: AuthUser) -> User:
    """First request after sign-up creates the users row (id = Supabase user id)."""
    user = await session.get(User, auth.id)
    if user is None:
        user = User(id=auth.id, email=auth.email.lower() if auth.email else None)
        session.add(user)
        await session.flush()
        await session.refresh(user)
    return user


PREFERENCE_FIELDS = ("full_name", "preferred_language", "text_size", "simple_mode")


async def update_preferences(session: AsyncSession, user: User, changes: dict[str, object]) -> User:
    before = {f: getattr(user, f) for f in PREFERENCE_FIELDS if f in changes}
    for field, value in changes.items():
        setattr(user, field, value)
    await session.flush()
    await audit.record(
        session,
        society_id=None,
        actor_user_id=user.id,
        action="user.preferences",
        entity_type="user",
        entity_id=user.id,
        before=before,
        after={f: getattr(user, f) for f in before},
    )
    return user


async def current_consents(session: AsyncSession, user: User) -> list[Consent]:
    version = get_settings().policy_version
    rows = await session.scalars(
        select(Consent).where(
            Consent.user_id == user.id,
            Consent.policy_version == version,
            Consent.withdrawn_at.is_(None),
        )
    )
    return list(rows)


def needs_consent(consents: list[Consent]) -> bool:
    granted = {c.purpose for c in consents}
    return not all(p in granted for p in REQUIRED_CONSENTS)


async def record_consents(
    session: AsyncSession, user: User, analytics: bool, notifications: bool
) -> list[Consent]:
    """Terms and privacy are required; analytics and notifications are opt-in choices.
    A choice turned off withdraws any earlier grant for the same policy version."""
    version = get_settings().policy_version
    existing = {c.purpose: c for c in await current_consents(session, user)}
    wanted = {
        "terms": True,
        "privacy": True,
        "analytics": analytics,
        "notifications": notifications,
    }
    now = datetime.now(UTC)
    for purpose, granted in wanted.items():
        if granted and purpose not in existing:
            session.add(Consent(user_id=user.id, purpose=purpose, policy_version=version))
        elif not granted and purpose in existing:
            existing[purpose].withdrawn_at = now
    user.analytics_opt_out = not analytics
    await session.flush()
    return await current_consents(session, user)
