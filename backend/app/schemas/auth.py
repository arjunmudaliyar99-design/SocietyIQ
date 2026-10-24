"""Signed-in user, preferences and consent (docs/02 §3, docs/05 §1)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Language = Literal["en", "mr", "hi", "gu", "ta"]
TextSize = Literal["normal", "large", "xlarge"]


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    full_name: str | None
    preferred_language: Language
    text_size: TextSize
    simple_mode: bool
    needs_consent: bool = False


class PreferencesIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    preferred_language: Language | None = None
    text_size: TextSize | None = None
    simple_mode: bool | None = None


class ConsentIn(BaseModel):
    """Accepting terms and privacy is implied by submitting the consent screen."""

    accept_terms_and_privacy: Literal[True]
    analytics: bool = False
    notifications: bool = False


class ConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    purpose: str
    policy_version: str
    granted_at: datetime


class ConsentStatusOut(BaseModel):
    policy_version: str
    needs_consent: bool
    granted: list[ConsentOut]
