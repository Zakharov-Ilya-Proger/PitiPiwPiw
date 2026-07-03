import os
from collections.abc import AsyncGenerator, Callable
from typing import Any

import pytest
import pytest_asyncio
from bcrypt import gensalt, hashpw
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Важно выставить env до импорта app.*, потому что настройки проекта читают env при импорте.
os.environ.setdefault("DB_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_PWD", "admin")
os.environ.setdefault("JWT_SECRET", "pytest-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")

from app.core import DB  # noqa: E402
from app.core.conf import settings  # noqa: E402

# В текущем приложении security.py использует settings.jwt_secret / jwt_algorithm /
# jwt_expire_minutes, но в Settings эти поля могут быть не объявлены. В тестах
# добавляем их к уже созданному объекту настроек без изменения кода приложения.
def _force_setting(name: str, value: Any) -> None:
    object.__setattr__(settings, name, value)


_force_setting("jwt_secret", os.environ["JWT_SECRET"])
_force_setting("jwt_algorithm", os.environ["JWT_ALGORITHM"])
_force_setting("jwt_expire_minutes", int(os.environ["JWT_EXPIRE_MINUTES"]))

from app.models import User  # noqa: E402
from app.main import app  # noqa: E402

API_PREFIX = "/api/v1"


def _role_value(role: str) -> Any:
    """Возвращает enum-роль, совместимую с текущей моделью пользователя."""
    try:
        from app.models.user import UserRole

        return getattr(UserRole, role)
    except Exception:
        pass

    try:
        from app.enums import Role

        return getattr(Role, role)
    except Exception:
        return role


def _password_hash(password: str) -> str:
    return hashpw(password.encode("utf-8"), gensalt()).decode("utf-8")


@pytest_asyncio.fixture()
async def session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(DB.metadata.create_all)

    try:
        yield TestingSessionLocal
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(DB.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture()
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    # Перекрываем оба возможных объекта зависимости: app.core.get_db и app.core.db.get_db.
    try:
        import app.core as core

        app.dependency_overrides[core.get_db] = override_get_db
    except Exception:
        pass

    try:
        import app.core.db as core_db

        app.dependency_overrides[core_db.get_db] = override_get_db
    except Exception:
        pass

    # Эти модули могли импортировать get_db напрямую, поэтому перекрываем и их
    # ссылки тоже. Это не меняет приложение, только изолирует тестовую БД.
    for module_path in (
        "app.core.security",
        "app.repositories.request_repo",
        "app.repositories.user_repo",
    ):
        try:
            module = __import__(module_path, fromlist=["get_db"])
            app.dependency_overrides[module.get_db] = override_get_db
        except Exception:
            pass

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def seed_user(
    session_factory: async_sessionmaker[AsyncSession],
) -> Callable[..., Any]:
    async def _seed_user(
        login: str,
        password: str = "password",
        role: str = "user",
    ) -> User:
        async with session_factory() as session:
            async with session.begin():
                user = User(
                    login=login,
                    hash_pwd=_password_hash(password),
                    role=_role_value(role),
                )
                session.add(user)
            await session.refresh(user)
            return user

    return _seed_user


@pytest_asyncio.fixture()
async def admin_user(seed_user: Callable[..., Any]) -> User:
    return await seed_user("admin", "admin", role="admin")


@pytest_asyncio.fixture()
async def regular_user(seed_user: Callable[..., Any]) -> User:
    return await seed_user("user", "password", role="user")


def extract_token(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        raise AssertionError(f"Не могу достать JWT из ответа: {payload!r}")

    for key in ("access_token", "token", "jwt"):
        token = payload.get(key)
        if token:
            return token

    nested = payload.get("data") or payload.get("result")
    if nested is not None:
        return extract_token(nested)

    raise AssertionError(f"В ответе логина нет access_token/token/jwt: {payload!r}")


async def login_headers(client: AsyncClient, login: str, password: str) -> dict[str, str]:
    response = await client.post(
        f"{API_PREFIX}/auth/login",
        data={"username": login, "password": password, 'grant_type': 'password'},
    )
    assert response.status_code == 200, response.text
    token = extract_token(response.json())
    return {"Authorization": f"Bearer {token}"}


def extract_request_id(payload: Any) -> int:
    if isinstance(payload, int):
        return payload
    if isinstance(payload, str) and payload.isdigit():
        return int(payload)
    if isinstance(payload, dict):
        for key in ("id", "request_id", "req_id"):
            value = payload.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
        for key in ("data", "result", "request"):
            if key in payload:
                return extract_request_id(payload[key])
    raise AssertionError(f"Не могу достать id заявки из ответа: {payload!r}")


def extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "results", "requests", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                return extract_items(value)
    raise AssertionError(f"Не могу достать список заявок из ответа: {payload!r}")


async def create_request(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    title: str = "Test request",
    description: str = "Test description",
    priority: str = "normal",
) -> int:
    response = await client.post(
        f"{API_PREFIX}/requests",
        json={
            "title": title,
            "description": description,
            "priority": priority,
        },
        headers=headers,
    )
    assert response.status_code in {200, 201}, response.text
    return extract_request_id(response.json())
