"""Tests for direct messaging endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.tests.conftest import auth_headers


@pytest.fixture()
def alice_headers(client):
    return auth_headers(client, username="alice", email="alice@example.com")


@pytest.fixture()
def bob_headers(client):
    return auth_headers(client, username="bob", email="bob@example.com", password="BobPass1!")


@pytest.fixture()
def alice_id(client, alice_headers):
    return client.get("/api/auth/me", headers=alice_headers).json()["id"]


@pytest.fixture()
def bob_id(client, bob_headers):
    return client.get("/api/auth/me", headers=bob_headers).json()["id"]


@pytest.fixture()
def dm(client, alice_headers, bob_id):
    resp = client.post(f"/api/dms?other_user_id={bob_id}", headers=alice_headers)
    assert resp.status_code == 200
    return resp.json()


class TestGetOrCreateDM:
    def test_create_dm_returns_200(self, client: TestClient, alice_headers, bob_id):
        resp = client.post(f"/api/dms?other_user_id={bob_id}", headers=alice_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["other_user"]["username"] == "bob"

    def test_get_or_create_is_idempotent(self, client: TestClient, alice_headers, bob_id):
        r1 = client.post(f"/api/dms?other_user_id={bob_id}", headers=alice_headers)
        r2 = client.post(f"/api/dms?other_user_id={bob_id}", headers=alice_headers)
        assert r1.json()["id"] == r2.json()["id"]

    def test_dm_with_self_is_rejected(self, client: TestClient, alice_headers, alice_id):
        resp = client.post(f"/api/dms?other_user_id={alice_id}", headers=alice_headers)
        assert resp.status_code == 400

    def test_dm_with_nonexistent_user_is_rejected(self, client: TestClient, alice_headers):
        resp = client.post("/api/dms?other_user_id=99999", headers=alice_headers)
        assert resp.status_code == 404

    def test_dm_requires_auth(self, client: TestClient, bob_id):
        resp = client.post(f"/api/dms?other_user_id={bob_id}")
        assert resp.status_code in (401, 403)

    def test_perspective_is_symmetric(self, client: TestClient, alice_headers, bob_headers, alice_id, bob_id):
        """Both sides see the same channel id with correct other_user."""
        r_alice = client.post(f"/api/dms?other_user_id={bob_id}", headers=alice_headers)
        r_bob = client.post(f"/api/dms?other_user_id={alice_id}", headers=bob_headers)
        assert r_alice.json()["id"] == r_bob.json()["id"]
        assert r_alice.json()["other_user"]["username"] == "bob"
        assert r_bob.json()["other_user"]["username"] == "alice"


class TestListDMs:
    def test_list_returns_created_dm(self, client: TestClient, alice_headers, dm):
        resp = client.get("/api/dms", headers=alice_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        ids = [d["id"] for d in data]
        assert dm["id"] in ids

    def test_list_requires_auth(self, client: TestClient):
        resp = client.get("/api/dms")
        assert resp.status_code in (401, 403)

    def test_list_does_not_include_others_dms(self, client: TestClient, alice_headers, bob_headers, dm):
        """A third user should see no DMs."""
        charlie_headers = auth_headers(
            client, username="charlie", email="charlie@example.com", password="CharliePass1!"
        )
        resp = client.get("/api/dms", headers=charlie_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestDMMessages:
    def test_send_dm_message(self, client: TestClient, alice_headers, dm):
        resp = client.post(
            f"/api/dms/{dm['id']}/messages",
            json={"content": "Hey Bob!"},
            headers=alice_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "Hey Bob!"
        assert data["dm_channel_id"] == dm["id"]

    def test_send_dm_message_empty_fails(self, client: TestClient, alice_headers, dm):
        resp = client.post(
            f"/api/dms/{dm['id']}/messages",
            json={"content": "   "},
            headers=alice_headers,
        )
        assert resp.status_code == 422

    def test_get_dm_messages(self, client: TestClient, alice_headers, dm):
        client.post(
            f"/api/dms/{dm['id']}/messages",
            json={"content": "Hello!"},
            headers=alice_headers,
        )
        resp = client.get(f"/api/dms/{dm['id']}/messages", headers=alice_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "messages" in data
        assert data["total"] >= 1

    def test_bob_can_also_message_alice(self, client: TestClient, bob_headers, dm):
        resp = client.post(
            f"/api/dms/{dm['id']}/messages",
            json={"content": "Hi Alice!"},
            headers=bob_headers,
        )
        assert resp.status_code == 200

    def test_nonparticipant_cannot_read_messages(self, client: TestClient, alice_headers, bob_headers, dm):
        charlie_headers = auth_headers(
            client, username="charlie2", email="charlie2@example.com", password="CharliePass1!"
        )
        resp = client.get(f"/api/dms/{dm['id']}/messages", headers=charlie_headers)
        assert resp.status_code == 403

    def test_nonparticipant_cannot_post_message(self, client: TestClient, bob_headers, dm):
        charlie_headers = auth_headers(
            client, username="charlie3", email="charlie3@example.com", password="CharliePass1!"
        )
        resp = client.post(
            f"/api/dms/{dm['id']}/messages",
            json={"content": "Intruding!"},
            headers=charlie_headers,
        )
        assert resp.status_code == 403

    def test_get_messages_for_nonexistent_dm(self, client: TestClient, alice_headers):
        resp = client.get("/api/dms/99999/messages", headers=alice_headers)
        assert resp.status_code == 404

    def test_dm_reply(self, client: TestClient, alice_headers, dm):
        """DM messages support reply_to_id within the same DM."""
        msg = client.post(
            f"/api/dms/{dm['id']}/messages",
            json={"content": "Original"},
            headers=alice_headers,
        ).json()

        resp = client.post(
            f"/api/dms/{dm['id']}/messages",
            json={"content": "Reply", "reply_to_id": msg["id"]},
            headers=alice_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply_to_id"] == msg["id"]

    def test_dm_reply_cross_channel_fails(self, client: TestClient, alice_headers, dm):
        """Cannot reply to a channel message from inside a DM."""
        channel = client.post("/api/channels", json={"name": "crosstest"}, headers=alice_headers).json()
        channel_msg = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "In channel"},
            headers=alice_headers,
        ).json()

        resp = client.post(
            f"/api/dms/{dm['id']}/messages",
            json={"content": "Cross reply", "reply_to_id": channel_msg["id"]},
            headers=alice_headers,
        )
        assert resp.status_code == 404
