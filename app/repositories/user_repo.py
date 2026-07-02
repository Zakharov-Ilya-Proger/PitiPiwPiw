from fastapi import Depends
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from bcrypt import hashpw, gensalt

from app.core import DBCreateUserError, DBError, DBNotFoundError, get_db
from app.schemas import User
from app.models import User as DBUser


class UserRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user: User):
        async with self.db.begin():
            data = {
                'login': user.login,
                'hash_pwd': hashpw(user.password.encode(), gensalt()).decode(),
            }
            try:
                result = await self.db.execute(
                    insert(DBUser)
                    .values(**data)
                    .returning(User.id)
                )
                res = result.scalar_one_or_none()
                if res is None:
                    raise DBCreateUserError('Error creating user')
                return res
            except IntegrityError as e:
                raise DBError(str(e))

    async def get_user(self, login: str):
        async with self.db.begin():
            try:
                result = await self.db.execute(
                    select(DBUser)
                    .where(DBUser.login == login)
                )
                res = result.scalar_one_or_none()
                if res is None:
                    raise DBNotFoundError('User does not exist')
                return res
            except IntegrityError as e:
                raise DBError(e)

async def get_user_repo(db: AsyncSession = Depends(get_db)):
    return UserRepo(db=db)
