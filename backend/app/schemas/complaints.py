"""Complaints and requests (docs/02 §8, docs/05 §5)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["water", "lift", "electricity", "cleaning", "security", "parking", "other"]
Location = Literal["my_flat", "common_area"]
Status = Literal["open", "in_progress", "resolved", "closed"]
Feedback = Literal["fixed", "not_fixed"]


class ComplaintIn(BaseModel):
    category: Category
    location: Location
    # Residents linked to one flat may leave it out; committee members raising on behalf of
    # a resident give it (docs/02 §8).
    flat_id: UUID | None = None
    description: str | None = Field(default=None, max_length=2000)


class ComplaintUpdateIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    new_status: Status | None = None
    visible_to_resident: bool = True


class AssignIn(BaseModel):
    assigned_to_text: str | None = Field(default=None, max_length=120)


class FeedbackIn(BaseModel):
    feedback: Feedback


class ComplaintUpdateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    message: str
    new_status: Status | None
    visible_to_resident: bool
    created_at: datetime


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flat_id: UUID | None
    flat_label: str | None = None
    raised_on_behalf: bool
    category: Category
    location: Location
    description: str | None
    status: Status
    assigned_to_text: str | None
    resident_feedback: Feedback | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None


class ComplaintDetailOut(ComplaintOut):
    updates: list[ComplaintUpdateOut] = Field(default_factory=list)
    photo_ids: list[UUID] = Field(default_factory=list)
    can_manage: bool = False
