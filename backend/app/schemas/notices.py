"""Notices and email (docs/02 §9, docs/05 §5)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Language = Literal["en", "mr", "hi", "gu", "ta"]
Audience = Literal["all", "owners", "tenants", "wing"]
NoticeStatus = Literal["draft", "published", "archived"]


class TranslationIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
    # Typed by a person = reviewed; AI translations stay unreviewed until a person says so.
    reviewed: bool = True


class TranslationOut(BaseModel):
    title: str
    body: str
    reviewed: bool


class NoticeIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
    language: Language = "en"
    audience: Audience = "all"
    audience_wing_id: UUID | None = None
    # Set when the text came from "Help me write".
    ai_assisted: bool = False


class NoticeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1, max_length=10000)
    language: Language | None = None
    audience: Audience | None = None
    audience_wing_id: UUID | None = None
    ai_assisted: bool | None = None
    # A language mapped to null removes that translation.
    translations: dict[Language, TranslationIn | None] | None = None


class NoticeOut(BaseModel):
    id: UUID
    title: str
    body: str
    language: Language
    audience: Audience
    audience_wing_id: UUID | None
    status: NoticeStatus
    ai_assisted: bool
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # For residents: whether they opened it (unread notices are shown in bold).
    is_read: bool = False


class NoticeDetailOut(NoticeOut):
    translations: dict[Language, TranslationOut] = Field(default_factory=dict)
    can_edit: bool = False
    can_publish: bool = False
    # Committee only.
    read_count: int | None = None
    recipient_count: int | None = None
    emails_sent: int | None = None
    emails_failed: int | None = None


class AiDraftIn(BaseModel):
    notes: str = Field(min_length=3, max_length=4000)
    language: Language = "en"


class AiTextOut(BaseModel):
    title: str
    body: str


class AiTranslateIn(BaseModel):
    languages: list[Language] = Field(min_length=1, max_length=4)


class NoticeOptionsOut(BaseModel):
    ai_available: bool
    # docs/02 §9: WhatsApp shows "Coming soon".
    whatsapp_available: bool = False
