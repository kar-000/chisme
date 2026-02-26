"""Tests for server nickname feature (PATCH/DELETE /users/me/servers/{id}/nickname)."""

from fastapi.testclient import TestClient

from .conftest import auth_headers, get_server_id

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_channel_id(client: TestClient, headers: dict, server_id: int) -> int:
    resp = client.get(f"/api/servers/{server_id}/channels", headers=headers)
    assert resp.status_code == 200
    channels = resp.json()
    assert channels
    return channels[0]["id"]


# ---------------------------------------------------------------------------
# Own nickname
# ---------------------------------------------------------------------------


def test_set_own_nickname(client):
    headers = auth_headers(client)
    server_id = get_server_id(client, headers)

    resp = client.patch(
        f"/api/users/me/servers/{server_id}/nickname",
        json={"nickname": "CoolNick"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "CoolNick"
    assert data["user_id"] is not None
    assert data["server_id"] == server_id


def test_nickname_appears_in_channel_messages(client):
    headers = auth_headers(client)
    server_id = get_server_id(client, headers)
    channel_id = get_channel_id(client, headers, server_id)

    # Set nickname first
    client.patch(
        f"/api/users/me/servers/{server_id}/nickname",
        json={"nickname": "MsgNick"},
        headers=headers,
    )

    # Send a message
    client.post(
        f"/api/servers/{server_id}/channels/{channel_id}/messages",
        json={"content": "hello from nick"},
        headers=headers,
    )

    # Fetch messages — display_name should be the nickname
    resp = client.get(f"/api/servers/{server_id}/channels/{channel_id}/messages", headers=headers)
    assert resp.status_code == 200
    messages = resp.json()["messages"]
    assert messages
    # The most recent message (last after reverse in store, first in desc query) is ours
    msg = next(m for m in messages if m["content"] == "hello from nick")
    assert msg["user"]["display_name"] == "MsgNick"


def test_nickname_too_long_rejected(client):
    headers = auth_headers(client)
    server_id = get_server_id(client, headers)

    resp = client.patch(
        f"/api/users/me/servers/{server_id}/nickname",
        json={"nickname": "A" * 33},
        headers=headers,
    )
    assert resp.status_code == 422


def test_clear_own_nickname(client):
    headers = auth_headers(client)
    server_id = get_server_id(client, headers)

    # Set then clear
    client.patch(
        f"/api/users/me/servers/{server_id}/nickname",
        json={"nickname": "Temp"},
        headers=headers,
    )

    resp = client.delete(
        f"/api/users/me/servers/{server_id}/nickname",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # After clearing, resolves to display_name or username
    assert data["display_name"] is not None  # falls back to username


def test_nickname_not_member_returns_404(client):
    """Setting nickname for a server the user isn't in returns 404."""
    headers = auth_headers(client)

    resp = client.patch(
        "/api/users/me/servers/99999/nickname",
        json={"nickname": "Ghost"},
        headers=headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Admin sets nickname for another user
# ---------------------------------------------------------------------------


def _register_second_user(client):
    """Register a second user and return their auth headers + user_id."""
    headers2 = auth_headers(
        client,
        username="memberuser",
        email="member@example.com",
        password="Password1!",
    )
    # Verify the second user is auto-joined to the main server
    servers_resp = client.get("/api/servers", headers=headers2)
    assert servers_resp.status_code == 200
    return headers2


def test_owner_sets_member_nickname(client):
    owner_headers = auth_headers(client)
    server_id = get_server_id(client, owner_headers)

    # Register second user (auto-joins the main server)
    _register_second_user(client)

    # Get member's user_id from the server member list
    members_resp = client.get(f"/api/servers/{server_id}/members", headers=owner_headers)
    assert members_resp.status_code == 200
    members = members_resp.json()
    member = next(m for m in members if m["username"] == "memberuser")
    member_user_id = member["user_id"]

    resp = client.patch(
        f"/api/users/{member_user_id}/servers/{server_id}/nickname",
        json={"nickname": "AdminChosen"},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "AdminChosen"


def test_member_cannot_set_another_members_nickname(client):
    owner_headers = auth_headers(client)
    server_id = get_server_id(client, owner_headers)

    member_headers = _register_second_user(client)

    # Get owner's user_id
    members_resp = client.get(f"/api/servers/{server_id}/members", headers=owner_headers)
    owner_id = next(m for m in members_resp.json() if m["role"] == "owner")["user_id"]

    resp = client.patch(
        f"/api/users/{owner_id}/servers/{server_id}/nickname",
        json={"nickname": "HackName"},
        headers=member_headers,
    )
    assert resp.status_code == 403


def test_nickname_resolves_in_member_list(client):
    owner_headers = auth_headers(client)
    server_id = get_server_id(client, owner_headers)

    # Set our own nickname
    client.patch(
        f"/api/users/me/servers/{server_id}/nickname",
        json={"nickname": "ListNick"},
        headers=owner_headers,
    )

    members_resp = client.get(f"/api/servers/{server_id}/members", headers=owner_headers)
    assert members_resp.status_code == 200
    members = members_resp.json()
    owner_entry = next(m for m in members if m["role"] == "owner")
    assert owner_entry["display_name"] == "ListNick"
