from datetime import datetime
from typing import TYPE_CHECKING
from enum import Enum as PyEnum

from sqlalchemy import Index, Integer, String, Enum, DateTime, func, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship, validates

from app.core import DB
from app.enums import Status, Priority

if TYPE_CHECKING:
    from app.models.user import User


class Request(DB):
    __tablename__ = 'requests'

    __table_args__ = (
        Index('ix_request_record', 'id', 'created_by', 'status', 'priority'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(length=120), nullable=False)
    description: Mapped[str] = mapped_column(String(length=1000), nullable=False)
    status: Mapped[Status] = mapped_column(Enum(Status), nullable=True, default=Status.new)
    priority: Mapped[Priority] = mapped_column(Enum(Priority), nullable=False)

    created_by: Mapped[int] = mapped_column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, onupdate=func.current_timestamp(),
                                                 default=None)

    @validates('title')
    def validate_title(self, key, value):
        if len(value) < 3:
            raise ValueError('Request title must be at least 3 characters')
        return value

    user: Mapped['User'] = relationship('User', back_populates='requests', foreign_keys=[created_by])
