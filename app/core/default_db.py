import asyncio

from sqlalchemy import insert, select
from bcrypt import hashpw, gensalt

from app.core import SessionLocal, settings
from app.enums import Role
from app.models.user import User

user_def_data = {
    'login': 'admin',
    'hash_pwd': hashpw(settings.admin_pwd.encode(), gensalt()).decode(),
    'role': Role.admin,
}

async def create():
    async with SessionLocal() as db:
        admin = await db.execute(select(User).where(User.login == Role.admin.value))
        if admin.scalar_one_or_none():
            print('Admin already exists')
            return
        await db.execute(
            insert(User)
            .values(**user_def_data)
        )
        await db.commit()

def main():
    asyncio.run(create())

main()