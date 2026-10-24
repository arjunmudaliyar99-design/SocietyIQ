"""Wings now; flats and members arrive in M3 (docs/05 §2)."""

from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedBy, Timestamps


class Wing(Timestamps, CreatedBy, Base):
    __tablename__ = "wings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    name: Mapped[str]
    has_lift: Mapped[bool] = mapped_column(server_default="false")
