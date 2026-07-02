from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import Index, UniqueConstraint, Integer, String, Enum
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.core import DB
from app.enums import Role

if TYPE_CHECKING:
    from app.models.request import Request


class User(DB):
    __tablename__ = 'user'

    __table_args__ = (
        UniqueConstraint('login'),
        Index('ix_user_record', 'login', 'id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String, nullable=False)
    hash_pwd: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)

    requests = relationship('Request', foreign_keys='Request.created_by', back_populates='user')
