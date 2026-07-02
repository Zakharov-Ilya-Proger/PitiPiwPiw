import pytest

from tests.conftest import (
    API_PREFIX,
    create_request,
    extract_items,
    login_headers,
)


@pytest.mark.asyncio
async def test_user_can_create_and_list_own_request(client, regular_user):
    headers = await login_headers(client, "user", "password")

    request_id = await create_request(
        client,
        headers,
        title="Printer is broken",
        description="Office printer does not work",
        priority="high",
    )

    response = await client.get(
        f"{API_PREFIX}/requests",
        params={"page": 1, "limit": 10},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    items = extract_items(response.json())
    assert any(item.get("id") == request_id for item in items)
    assert any(item.get("title") == "Printer is broken" for item in items)


@pytest.mark.asyncio
async def test_regular_users_see_only_their_own_requests(client, seed_user, admin_user):
    await seed_user("alice", "password", role="user")
    await seed_user("bob", "password", role="user")

    alice_headers = await login_headers(client, "alice", "password")
    bob_headers = await login_headers(client, "bob", "password")
    admin_headers = await login_headers(client, "admin", "admin")

    await create_request(client, alice_headers, title="Alice private request", priority="low")
    await create_request(client, bob_headers, title="Bob private request", priority="high")

    alice_response = await client.get(
        f"{API_PREFIX}/requests",
        params={"page": 1, "limit": 10},
        headers=alice_headers,
    )
    bob_response = await client.get(
        f"{API_PREFIX}/requests",
        params={"page": 1, "limit": 10},
        headers=bob_headers,
    )
    admin_response = await client.get(
        f"{API_PREFIX}/requests",
        params={"page": 1, "limit": 10},
        headers=admin_headers,
    )

    assert alice_response.status_code == 200, alice_response.text
    assert bob_response.status_code == 200, bob_response.text
    assert admin_response.status_code == 200, admin_response.text

    alice_titles = {item.get("title") for item in extract_items(alice_response.json())}
    bob_titles = {item.get("title") for item in extract_items(bob_response.json())}
    admin_titles = {item.get("title") for item in extract_items(admin_response.json())}

    assert "Alice private request" in alice_titles
    assert "Bob private request" not in alice_titles

    assert "Bob private request" in bob_titles
    assert "Alice private request" not in bob_titles

    assert {"Alice private request", "Bob private request"}.issubset(admin_titles)


@pytest.mark.asyncio
async def test_filter_search_sort_and_pagination(client, regular_user):
    headers = await login_headers(client, "user", "password")

    await create_request(client, headers, title="Alpha low", description="printer", priority="low")
    await create_request(client, headers, title="Beta high", description="network", priority="high")
    await create_request(client, headers, title="Gamma high", description="network urgent", priority="high")

    filtered_response = await client.get(
        f"{API_PREFIX}/requests",
        params={
            "priority": "high",
            "page": 1,
            "limit": 10,
            "sort_priority": True,
            "sort_date": False,
        },
        headers=headers,
    )
    assert filtered_response.status_code == 200, filtered_response.text
    filtered_items = extract_items(filtered_response.json())
    assert len(filtered_items) >= 2
    assert all(item.get("priority") == "high" for item in filtered_items)

    search_response = await client.get(
        f"{API_PREFIX}/requests",
        params={"description": "network", "page": 1, "limit": 10},
        headers=headers,
    )
    assert search_response.status_code == 200, search_response.text
    search_titles = {item.get("title") for item in extract_items(search_response.json())}
    assert "Beta high" in search_titles
    assert "Gamma high" in search_titles
    assert "Alpha low" not in search_titles

    page_response = await client.get(
        f"{API_PREFIX}/requests",
        params={"page": 1, "limit": 2},
        headers=headers,
    )
    assert page_response.status_code == 200, page_response.text
    assert len(extract_items(page_response.json())) <= 2


@pytest.mark.asyncio
async def test_user_can_update_own_status_but_cannot_move_done_back(client, regular_user):
    headers = await login_headers(client, "user", "password")
    request_id = await create_request(client, headers, title="Status flow request")

    in_progress_response = await client.patch(
        f"{API_PREFIX}/requests/status",
        json={"req_id": request_id, "target_status": "in_progress"},
        headers=headers,
    )
    assert in_progress_response.status_code == 200, in_progress_response.text

    done_response = await client.patch(
        f"{API_PREFIX}/requests/status",
        json={"req_id": request_id, "target_status": "done"},
        headers=headers,
    )
    assert done_response.status_code == 200, done_response.text

    rollback_response = await client.patch(
        f"{API_PREFIX}/requests/status",
        json={"req_id": request_id, "target_status": "in_progress"},
        headers=headers,
    )
    assert rollback_response.status_code in {400, 403, 409}, rollback_response.text


@pytest.mark.asyncio
async def test_user_cannot_update_another_users_request(client, seed_user):
    await seed_user("alice", "password", role="user")
    await seed_user("bob", "password", role="user")

    alice_headers = await login_headers(client, "alice", "password")
    bob_headers = await login_headers(client, "bob", "password")

    request_id = await create_request(client, alice_headers, title="Alice protected request")

    response = await client.patch(
        f"{API_PREFIX}/requests/status",
        json={"req_id": request_id, "target_status": "in_progress"},
        headers=bob_headers,
    )

    assert response.status_code in {403, 404}, response.text


@pytest.mark.asyncio
async def test_only_admin_can_delete_not_done_request(client, regular_user, admin_user):
    user_headers = await login_headers(client, "user", "password")
    admin_headers = await login_headers(client, "admin", "admin")

    request_id = await create_request(client, user_headers, title="Delete me", priority="normal")

    user_delete_response = await client.delete(
        f"{API_PREFIX}/requests/{request_id}",
        headers=user_headers,
    )
    assert user_delete_response.status_code in {401, 403}, user_delete_response.text

    admin_delete_response = await client.delete(
        f"{API_PREFIX}/requests/{request_id}",
        headers=admin_headers,
    )
    assert admin_delete_response.status_code in {200, 204}, admin_delete_response.text

    list_response = await client.get(
        f"{API_PREFIX}/requests",
        params={"page": 1, "limit": 10},
        headers=admin_headers,
    )
    assert list_response.status_code == 200, list_response.text
    titles = {item.get("title") for item in extract_items(list_response.json())}
    assert "Delete me" not in titles


@pytest.mark.asyncio
async def test_done_request_cannot_be_deleted_even_by_admin(client, regular_user, admin_user):
    user_headers = await login_headers(client, "user", "password")
    admin_headers = await login_headers(client, "admin", "admin")

    request_id = await create_request(client, user_headers, title="Done request")
    done_response = await client.patch(
        f"{API_PREFIX}/requests/status",
        json={"req_id": request_id, "target_status": "done"},
        headers=user_headers,
    )
    assert done_response.status_code == 200, done_response.text

    delete_response = await client.delete(
        f"{API_PREFIX}/requests/{request_id}",
        headers=admin_headers,
    )

    assert delete_response.status_code in {400, 403, 409}, delete_response.text


@pytest.mark.asyncio
async def test_create_request_validation_errors(client, regular_user):
    headers = await login_headers(client, "user", "password")

    short_title_response = await client.post(
        f"{API_PREFIX}/requests",
        json={"title": "ab", "description": "valid", "priority": "normal"},
        headers=headers,
    )
    assert short_title_response.status_code == 422, short_title_response.text

    long_description_response = await client.post(
        f"{API_PREFIX}/requests",
        json={
            "title": "Valid title",
            "description": "x" * 1001,
            "priority": "normal",
        },
        headers=headers,
    )
    assert long_description_response.status_code == 422, long_description_response.text

    invalid_priority_response = await client.post(
        f"{API_PREFIX}/requests",
        json={"title": "Valid title", "description": "valid", "priority": "critical"},
        headers=headers,
    )
    assert invalid_priority_response.status_code == 422, invalid_priority_response.text
