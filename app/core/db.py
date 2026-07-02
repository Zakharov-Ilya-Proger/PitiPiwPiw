from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core import settings


class DB(DeclarativeBase):
    pass

engine = create_async_engine(
    settings.db_url,
    connect_args={'check_same_thread': False},
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

__all__ = [
    'get_db',
    'DB',
    'SessionLocal',
]
