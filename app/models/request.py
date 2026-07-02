from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core import DB
from app.enums import Priority, Status

if TYPE_CHECKING:
    from app.models.user import User


class Request(DB):
    __tablename__ = "requests"
    __table_args__ = (
        Index("ix_request_record", "id", "created_by", "status", "priority"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(length=120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(length=1000), nullable=True)
    status: Mapped[Status] = mapped_column(Enum(Status), nullable=False, default=Status.new)
    priority: Mapped[Priority] = mapped_column(Enum(Priority), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=func.current_timestamp(), default=None)

    user: Mapped["User"] = relationship("User", back_populates="requests", foreign_keys=[created_by])

    @validates("title")
    def validate_title(self, key: str, value: str) -> str:
        if len(value) < 3:
            raise ValueError("Request title must be at least 3 characters")
        return value
