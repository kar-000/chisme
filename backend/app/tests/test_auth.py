"""Tests for /api/auth endpoints."""

from fastapi.testclient import TestClient

from app.tests.conftest import auth_headers, get_server_id, register_user


class TestRegister:
    def test_register_success(self, client: TestClient):
        resp = register_user(client)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "testuser"

    def test_register_duplicate_username(self, client: TestClient):
        register_user(client)
        resp = register_user(client)
        assert resp.status_code == 409
        assert "Username" in resp.json()["detail"]

    def test_register_duplicate_email(self, client: TestClient):
        register_user(client, username="user1")
        resp = register_user(client, username="user2")
        assert resp.status_code == 409

    def test_register_weak_password_no_number(self, client: TestClient):
        resp = register_user(client, password="NoNumber!")
        assert resp.status_code == 422

    def test_register_weak_password_no_special(self, client: TestClient):
        resp = register_user(client, password="NoSpecial1")
        assert resp.status_code == 422

    def test_register_invalid_username_chars(self, client: TestClient):
        resp = register_user(client, username="bad user!")
        assert resp.status_code == 422

    def test_register_username_too_short(self, client: TestClient):
        resp = register_user(client, username="ab")
        assert resp.status_code == 422

    def test_register_creates_general_channel(self, client: TestClient):
        reg = register_user(client)
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        server_id = get_server_id(client, headers)
        channels_resp = client.get(f"/api/servers/{server_id}/channels", headers=headers)
        names = [c["name"] for c in channels_resp.json()]
        assert "general" in names


class TestLogin:
    def test_login_success(self, client: TestClient):
        register_user(client)
        resp = client.post("/api/auth/login", json={"username": "testuser", "password": "Password1!"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client: TestClient):
        register_user(client)
        resp = client.post("/api/auth/login", json={"username": "testuser", "password": "WrongPass1!"})
        assert resp.status_code == 400

    def test_login_unknown_user(self, client: TestClient):
        resp = client.post("/api/auth/login", json={"username": "nobody", "password": "Password1!"})
        assert resp.status_code == 400


class TestGetMe:
    def test_get_me_success(self, client: TestClient):
        headers = auth_headers(client)
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "testuser"

    def test_get_me_no_token(self, client: TestClient):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 403

    def test_get_me_bad_token(self, client: TestClient):
        # Invalid JWT → 401 from our get_current_user dependency
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer badtoken"})
        assert resp.status_code == 401
