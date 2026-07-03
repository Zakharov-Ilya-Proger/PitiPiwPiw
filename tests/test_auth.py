import pytest

from tests.conftest import API_PREFIX, extract_token, login_headers


@pytest.mark.asyncio
async def test_login_returns_jwt_token(client, regular_user):
    response = await client.post(
        f"{API_PREFIX}/auth/login",
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        data={
            'grant_type': 'password',
            "username": "user",
            "password": "password"
        }
    )

    assert response.status_code == 200, response.text
    token = extract_token(response.json())
    assert isinstance(token, str)
    assert token.count(".") == 2


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client, regular_user):
    response = await client.post(
        f"{API_PREFIX}/auth/login",
        data={
            'grant_type': 'password',
            "username": "user",
            "password": "wrong-password"
        },
    )

    assert response.status_code in {400, 401, 403}, response.text


@pytest.mark.asyncio
async def test_protected_requests_endpoint_requires_token(client):
    response = await client.get(f"{API_PREFIX}/requests")

    assert response.status_code in {401, 403}, response.text


@pytest.mark.asyncio
async def test_auth_me_returns_current_user(client, regular_user):
    headers = await login_headers(client, "user", "password")

    response = await client.get(f"{API_PREFIX}/auth/me", headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("login") == "user" or payload.get("data", {}).get("login") == "user"
