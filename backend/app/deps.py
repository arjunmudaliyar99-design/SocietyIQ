"""Request dependencies: signed-in user, tenant context, roles (docs/04 §5-6)."""

from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthUser, verify_token
from app.db import set_society_context, set_user_context, transaction
from app.errors import AppError, not_found
from app.models import User
from app.services import auth as user_service
from app.services import societies as membership_service


def get_auth_user(authorization: Annotated[str | None, Header()] = None) -> AuthUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "UNAUTHORIZED", "errors.signInAgain")
    return verify_token(authorization[7:].strip())


AuthDep = Annotated[AuthUser, Depends(get_auth_user)]


async def get_session(auth: AuthDep) -> AsyncIterator[AsyncSession]:
    async for session in transaction():
        await set_user_context(session, auth.id)
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(auth: AuthDep, session: SessionDep) -> User:
    return await user_service.ensure_user(session, auth)


CurrentUserDep = Annotated[User, Depends(get_current_user)]


@dataclass(frozen=True)
class SocietyContext:
    society_id: UUID
    user: User
    roles: frozenset[str]


def require_role(
    *allowed: str,
) -> Callable[..., Coroutine[Any, Any, SocietyContext]]:
    """Society routes: 404 for non-members (never confirm the society exists), 403 for
    members without one of the allowed roles. With no roles given, any active member passes."""

    async def dependency(
        society_id: UUID, user: CurrentUserDep, session: SessionDep
    ) -> SocietyContext:
        await set_society_context(session, society_id)
        roles = await membership_service.active_roles(session, society_id, user.id)
        if not roles:
            raise not_found()
        if allowed and not roles.intersection(allowed):
            raise AppError(403, "FORBIDDEN", "errors.notAllowed")
        return SocietyContext(society_id=society_id, user=user, roles=frozenset(roles))

    return dependency
