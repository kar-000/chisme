"""Tests for message and reaction endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.tests.conftest import auth_headers


@pytest.fixture()
def headers(client):
    return auth_headers(client)


@pytest.fixture()
def channel(client, headers):
    resp = client.post("/api/channels", json={"name": "msg-room"}, headers=headers)
    return resp.json()


@pytest.fixture()
def message(client, headers, channel):
    resp = client.post(
        f"/api/channels/{channel['id']}/messages",
        json={"content": "Hello, chisme!"},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


class TestSendMessage:
    def test_send_success(self, client: TestClient, headers, channel):
        resp = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "Hello world"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "Hello world"

    def test_send_to_nonexistent_channel(self, client: TestClient, headers):
        resp = client.post("/api/channels/9999/messages", json={"content": "Hi"}, headers=headers)
        assert resp.status_code == 404

    def test_send_empty_content(self, client: TestClient, headers, channel):
        resp = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": ""},
            headers=headers,
        )
        assert resp.status_code == 422


class TestGetMessages:
    def test_get_messages(self, client: TestClient, headers, channel, message):
        resp = client.get(f"/api/channels/{channel['id']}/messages", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "messages" in data
        assert data["total"] >= 1

    def test_pagination(self, client: TestClient, headers, channel):
        for i in range(5):
            client.post(
                f"/api/channels/{channel['id']}/messages",
                json={"content": f"msg {i}"},
                headers=headers,
            )
        resp = client.get(f"/api/channels/{channel['id']}/messages?limit=2&offset=0", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()["messages"]) == 2


class TestEditMessage:
    def test_edit_own_message(self, client: TestClient, headers, message):
        resp = client.put(f"/api/messages/{message['id']}", json={"content": "Edited!"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["content"] == "Edited!"
        assert resp.json()["edited_at"] is not None

    def test_edit_others_message(self, client: TestClient, headers, channel):
        # A second user must not be able to edit another user's message
        headers2 = auth_headers(client, username="other2", email="other2@example.com", password="OtherPass2!")
        msg = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "mine"},
            headers=headers,
        ).json()
        resp = client.put(f"/api/messages/{msg['id']}", json={"content": "stolen"}, headers=headers2)
        assert resp.status_code == 403

    def test_edit_nonexistent_message(self, client: TestClient, headers):
        resp = client.put("/api/messages/9999", json={"content": "Hi"}, headers=headers)
        assert resp.status_code == 404


class TestDeleteMessage:
    def test_delete_own_message(self, client: TestClient, headers, message):
        resp = client.delete(f"/api/messages/{message['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_delete_nonexistent_message(self, client: TestClient, headers):
        resp = client.delete("/api/messages/9999", headers=headers)
        assert resp.status_code == 404


class TestReactions:
    def test_add_reaction(self, client: TestClient, headers, message):
        resp = client.post(
            f"/api/messages/{message['id']}/reactions",
            json={"emoji": "👍"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["emoji"] == "👍"

    def test_add_duplicate_reaction(self, client: TestClient, headers, message):
        client.post(f"/api/messages/{message['id']}/reactions", json={"emoji": "👍"}, headers=headers)
        resp = client.post(f"/api/messages/{message['id']}/reactions", json={"emoji": "👍"}, headers=headers)
        assert resp.status_code == 409

    def test_remove_reaction(self, client: TestClient, headers, message):
        client.post(f"/api/messages/{message['id']}/reactions", json={"emoji": "❤️"}, headers=headers)
        resp = client.delete(f"/api/messages/{message['id']}/reactions/❤️", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_remove_nonexistent_reaction(self, client: TestClient, headers, message):
        resp = client.delete(f"/api/messages/{message['id']}/reactions/🙃", headers=headers)
        assert resp.status_code == 404
