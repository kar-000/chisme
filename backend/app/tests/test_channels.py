"""Tests for /api/servers/{server_id}/channels endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.tests.conftest import auth_headers, get_server_id


@pytest.fixture()
def headers(client):
    return auth_headers(client)


@pytest.fixture()
def server_id(client, headers):
    return get_server_id(client, headers)


@pytest.fixture()
def channel(client, headers, server_id):
    resp = client.post(
        f"/api/servers/{server_id}/channels",
        json={"name": "test-room", "description": "A test channel"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    data["server_id"] = server_id
    return data


class TestCreateChannel:
    def test_create_success(self, client: TestClient, headers, server_id):
        resp = client.post(f"/api/servers/{server_id}/channels", json={"name": "my-channel"}, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "my-channel"
        assert "id" in data

    def test_create_duplicate_name(self, client: TestClient, headers, channel):
        resp = client.post(
            f"/api/servers/{channel['server_id']}/channels",
            json={"name": "test-room"},
            headers=headers,
        )
        assert resp.status_code == 409

    def test_create_invalid_name_uppercase(self, client: TestClient, headers, server_id):
        resp = client.post(f"/api/servers/{server_id}/channels", json={"name": "BadName"}, headers=headers)
        # Validator lowercases it — name becomes "badname" which is valid
        assert resp.status_code == 201

    def test_create_invalid_name_spaces(self, client: TestClient, headers, server_id):
        resp = client.post(f"/api/servers/{server_id}/channels", json={"name": "bad name"}, headers=headers)
        assert resp.status_code == 422

    def test_create_requires_auth(self, client: TestClient, server_id):
        resp = client.post(f"/api/servers/{server_id}/channels", json={"name": "noauth"})
        assert resp.status_code == 403


class TestListChannels:
    def test_list_returns_channels(self, client: TestClient, headers, channel):
        resp = client.get(f"/api/servers/{channel['server_id']}/channels", headers=headers)
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()]
        assert "test-room" in names

    def test_list_requires_auth(self, client: TestClient, server_id):
        resp = client.get(f"/api/servers/{server_id}/channels")
        assert resp.status_code == 403


class TestGetChannel:
    def test_get_existing_channel(self, client: TestClient, headers, channel):
        resp = client.get(f"/api/servers/{channel['server_id']}/channels/{channel['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "test-room"

    def test_get_nonexistent_channel(self, client: TestClient, headers, server_id):
        resp = client.get(f"/api/servers/{server_id}/channels/9999", headers=headers)
        assert resp.status_code == 404
