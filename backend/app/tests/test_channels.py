"""Tests for /api/channels endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.tests.conftest import auth_headers, register_user


@pytest.fixture()
def headers(client):
    return auth_headers(client)


@pytest.fixture()
def channel(client, headers):
    resp = client.post("/api/channels", json={"name": "test-room", "description": "A test channel"}, headers=headers)
    assert resp.status_code == 200
    return resp.json()


class TestCreateChannel:
    def test_create_success(self, client: TestClient, headers):
        resp = client.post("/api/channels", json={"name": "my-channel"}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "my-channel"
        assert "id" in data

    def test_create_duplicate_name(self, client: TestClient, headers, channel):
        resp = client.post("/api/channels", json={"name": "test-room"}, headers=headers)
        assert resp.status_code == 409

    def test_create_invalid_name_uppercase(self, client: TestClient, headers):
        resp = client.post("/api/channels", json={"name": "BadName"}, headers=headers)
        # Validator lowercases it — name becomes "badname" which is valid
        assert resp.status_code == 200

    def test_create_invalid_name_spaces(self, client: TestClient, headers):
        resp = client.post("/api/channels", json={"name": "bad name"}, headers=headers)
        assert resp.status_code == 422

    def test_create_requires_auth(self, client: TestClient):
        resp = client.post("/api/channels", json={"name": "noauth"})
        assert resp.status_code == 403


class TestListChannels:
    def test_list_returns_channels(self, client: TestClient, headers, channel):
        resp = client.get("/api/channels", headers=headers)
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()]
        assert "test-room" in names

    def test_list_requires_auth(self, client: TestClient):
        resp = client.get("/api/channels")
        assert resp.status_code == 403


class TestGetChannel:
    def test_get_existing_channel(self, client: TestClient, headers, channel):
        resp = client.get(f"/api/channels/{channel['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "test-room"

    def test_get_nonexistent_channel(self, client: TestClient, headers):
        resp = client.get("/api/channels/9999", headers=headers)
        assert resp.status_code == 404
