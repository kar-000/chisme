"""
Tests for operator (site admin) endpoints and WebSocket suspension enforcement.

Covers:
  - GET  /api/operator/servers  (list all servers)
  - POST /api/operator/servers/{id}/suspend
  - POST /api/operator/servers/{id}/unsuspend
  - DELETE /api/operator/servers/{id}
  - POST /api/operator/servers/{id}/reassign-owner
  - GET  /api/operator/users
  - POST /api/operator/users/{id}/disable
  - POST /api/operator/users/{id}/enable
  - WebSocket: suspended server rejects connections with 4003
"""

import pytest
from fastapi.testclient import TestClient

from app.models.user import User
from app.tests.conftest import auth_headers, register_user


def _make_admin(db, username: str) -> None:
    """Promote a registered user to site admin directly via DB."""
    user = db.query(User).filter(User.username == username).first()
    assert user is not None, f"User {username!r} not found"
    user.is_site_admin = True
    db.commit()


def _create_server(client, headers, slug="opsrv"):
    resp = client.post(
        "/api/servers",
        json={"name": "Op Test", "slug": slug},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_invite(client, headers, server_id):
    resp = client.post(f"/api/servers/{server_id}/invites", json={}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------


class TestOperatorAuth:
    def test_list_servers_requires_site_admin(self, client: TestClient):
        headers = auth_headers(client, username="opnonadmin", email="opnonadmin@example.com")
        resp = client.get("/api/operator/servers", headers=headers)
        assert resp.status_code == 403

    def test_list_users_requires_site_admin(self, client: TestClient):
        headers = auth_headers(client, username="opnonadmin2", email="opnonadmin2@example.com")
        resp = client.get("/api/operator/users", headers=headers)
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self, client: TestClient):
        resp = client.get("/api/operator/servers")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------


class TestOperatorServers:
    def test_list_all_servers(self, client: TestClient, db):
        headers = auth_headers(client, username="oplistadm", email="oplistadm@example.com")
        _make_admin(db, "oplistadm")

        auth_headers(client, username="oplistusr", email="oplistusr@example.com")
        resp = client.get("/api/operator/servers", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all("member_count" in s for s in data)

    def test_suspend_server(self, client: TestClient, db):
        headers = auth_headers(client, username="opsusadm", email="opsusadm@example.com")
        _make_admin(db, "opsusadm")
        server = _create_server(client, headers, slug="opsussr")

        resp = client.post(
            f"/api/operator/servers/{server['id']}/suspend",
            json={"reason": "Violation of ToS"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "suspended"

    def test_suspend_requires_reason(self, client: TestClient, db):
        headers = auth_headers(client, username="opnoreason", email="opnoreason@example.com")
        _make_admin(db, "opnoreason")
        server = _create_server(client, headers, slug="opnoreasonsrv")

        resp = client.post(
            f"/api/operator/servers/{server['id']}/suspend",
            json={},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_suspend_empty_reason_rejected(self, client: TestClient, db):
        headers = auth_headers(client, username="opemptyr", email="opemptyr@example.com")
        _make_admin(db, "opemptyr")
        server = _create_server(client, headers, slug="opemptyrsrv")

        resp = client.post(
            f"/api/operator/servers/{server['id']}/suspend",
            json={"reason": ""},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_unsuspend_server(self, client: TestClient, db):
        headers = auth_headers(client, username="opunsusadm", email="opunsusadm@example.com")
        _make_admin(db, "opunsusadm")
        server = _create_server(client, headers, slug="opunsussr")

        client.post(
            f"/api/operator/servers/{server['id']}/suspend",
            json={"reason": "Test"},
            headers=headers,
        )
        resp = client.post(
            f"/api/operator/servers/{server['id']}/unsuspend",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_operator_delete_server(self, client: TestClient, db):
        headers = auth_headers(client, username="opdeladm", email="opdeladm@example.com")
        _make_admin(db, "opdeladm")
        server = _create_server(client, headers, slug="opdelsrv")

        resp = client.delete(f"/api/operator/servers/{server['id']}", headers=headers)
        assert resp.status_code == 204

    def test_reassign_owner(self, client: TestClient, db):
        h_admin = auth_headers(client, username="opreasadm", email="opreasadm@example.com")
        _make_admin(db, "opreasadm")
        server = _create_server(client, headers=h_admin, slug="opreassrv")

        h_new = auth_headers(client, username="opreasnew", email="opreasnew@example.com")
        new_user = client.get("/api/auth/me", headers=h_new).json()

        resp = client.post(
            f"/api/operator/servers/{server['id']}/reassign-owner",
            json={"new_owner_id": new_user["id"]},
            headers=h_admin,
        )
        assert resp.status_code == 200
        assert resp.json()["new_owner_id"] == new_user["id"]

    def test_reassign_owner_missing_user(self, client: TestClient, db):
        headers = auth_headers(client, username="opreasbad", email="opreasbad@example.com")
        _make_admin(db, "opreasbad")
        server = _create_server(client, headers, slug="opreasbadsrv")

        resp = client.post(
            f"/api/operator/servers/{server['id']}/reassign-owner",
            json={"new_owner_id": 99999},
            headers=headers,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


class TestOperatorUsers:
    def test_list_all_users(self, client: TestClient, db):
        headers = auth_headers(client, username="opusradm", email="opusradm@example.com")
        _make_admin(db, "opusradm")

        resp = client.get("/api/operator/users", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(u["username"] == "opusradm" for u in data)
        assert all("server_count" in u for u in data)

    def test_disable_user(self, client: TestClient, db):
        h_admin = auth_headers(client, username="opdisadm", email="opdisadm@example.com")
        _make_admin(db, "opdisadm")

        h_target = auth_headers(client, username="opdistgt", email="opdistgt@example.com")
        target = client.get("/api/auth/me", headers=h_target).json()

        resp = client.post(f"/api/operator/users/{target['id']}/disable", headers=h_admin)
        assert resp.status_code == 200
        assert resp.json()["status"] == "disabled"

    def test_enable_user(self, client: TestClient, db):
        h_admin = auth_headers(client, username="openaadm", email="openaadm@example.com")
        _make_admin(db, "openaadm")

        h_target = auth_headers(client, username="openatgt", email="openatgt@example.com")
        target = client.get("/api/auth/me", headers=h_target).json()

        client.post(f"/api/operator/users/{target['id']}/disable", headers=h_admin)
        resp = client.post(f"/api/operator/users/{target['id']}/enable", headers=h_admin)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_cannot_disable_site_admin(self, client: TestClient, db):
        h_admin1 = auth_headers(client, username="opa1", email="opa1@example.com")
        h_admin2 = auth_headers(client, username="opa2", email="opa2@example.com")
        _make_admin(db, "opa1")
        _make_admin(db, "opa2")

        admin2 = client.get("/api/auth/me", headers=h_admin2).json()
        resp = client.post(f"/api/operator/users/{admin2['id']}/disable", headers=h_admin1)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# WebSocket suspension check
# ---------------------------------------------------------------------------


class TestSuspendedServerWebSocket:
    def test_suspended_server_rejects_ws_with_4003(self, client: TestClient, db):
        """Server WS handler closes with code 4003 for suspended servers."""
        h_admin = auth_headers(client, username="opwsadm", email="opwsadm@example.com")
        _make_admin(db, "opwsadm")

        token = register_user(client, username="opwstok", email="opwstok@example.com").json()["access_token"]
        tok_headers = {"Authorization": f"Bearer {token}"}

        server = _create_server(client, h_admin, slug="opwssrv")
        invite = _create_invite(client, h_admin, server["id"])
        client.post(f"/api/invites/{invite['code']}/redeem", headers=tok_headers)

        # Suspend the server
        client.post(
            f"/api/operator/servers/{server['id']}/suspend",
            json={"reason": "WS test"},
            headers=h_admin,
        )

        # WebSocket connection should be rejected
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/server/{server['id']}") as ws:
                ws.send_json({"type": "auth", "token": token})
                ws.receive_json()
