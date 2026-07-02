from datetime import datetime, timedelta
from typing import Any

import jwt
from bcrypt import checkpw
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.conf import settings
from app.core.db import get_db
from app.models import User as DBUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')


def verify_password(password: str, hashed_password: str) -> bool:
    return checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: dict[str, Any]) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)

    payload.update({'exp': expire})
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token expired',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token',
            headers={'WWW-Authenticate': 'Bearer'}
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> DBUser:
    payload = decode_access_token(token)
    user_id = payload.get('sub')
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='В токене отсутствует идентификатор пользователя',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    from sqlalchemy import select

    result = await db.execute(select(DBUser).where(DBUser.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Пользователь не найден')
    return user

__all__=[
    'get_current_user',
    'verify_password',
    'create_access_token',
    'decode_access_token'
]
