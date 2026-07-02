import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from bcrypt import checkpw, gensalt, hashpw
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.conf import settings
from app.core.db import get_db
from app.models import User as DBUser


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')


def hash_password(password: str) -> str:
    return hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    return checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(data: dict[str, Any]) -> str:
    header = {'alg': settings.jwt_algorithm, 'typ': 'JWT'}
    payload = data.copy()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload['exp'] = int(expires_at.timestamp())

    header_part = _b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_part = _b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signing_input = f'{header_part}.{payload_part}'.encode('ascii')
    signature = hmac.new(settings.jwt_secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_part = _b64url_encode(signature)
    return f'{header_part}.{payload_part}.{signature_part}'


def decode_access_token(token: str) -> dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Не удалось проверить токен авторизации',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    try:
        header_part, payload_part, signature_part = token.split('.')
    except ValueError as exc:
        raise credentials_exception from exc

    signing_input = f'{header_part}.{payload_part}'.encode('ascii')
    expected_signature = hmac.new(settings.jwt_secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    actual_signature = _b64url_decode(signature_part)

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise credentials_exception

    try:
        payload = json.loads(_b64url_decode(payload_part))
    except (json.JSONDecodeError, ValueError) as exc:
        raise credentials_exception from exc

    exp = payload.get('exp')
    if exp is None or datetime.now(timezone.utc).timestamp() > int(exp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Срок действия токена истёк',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    return payload


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
