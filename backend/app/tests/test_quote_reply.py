"""Tests for quote-reply (reply_to_id) on channel messages."""

import pytest
from fastapi.testclient import TestClient

from app.tests.conftest import auth_headers


@pytest.fixture()
def headers(client):
    return auth_headers(client)


@pytest.fixture()
def channel(client, headers):
    resp = client.post("/api/channels", json={"name": "reply-room"}, headers=headers)
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture()
def message(client, headers, channel):
    resp = client.post(
        f"/api/channels/{channel['id']}/messages",
        json={"content": "Original message"},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


class TestQuoteReply:
    def test_reply_to_message_success(self, client: TestClient, headers, channel, message):
        resp = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "This is a reply", "reply_to_id": message["id"]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply_to_id"] == message["id"]
        assert data["reply_to"] is not None
        assert data["reply_to"]["id"] == message["id"]
        assert data["reply_to"]["content"] == "Original message"

    def test_reply_includes_author_info(self, client: TestClient, headers, channel, message):
        resp = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "Reply with author info", "reply_to_id": message["id"]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply_to"]["user"]["username"] == "testuser"

    def test_reply_to_nonexistent_message_fails(self, client: TestClient, headers, channel):
        resp = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "Orphan reply", "reply_to_id": 99999},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_reply_to_message_in_other_channel_fails(self, client: TestClient, headers, message):
        # Create a different channel
        other_channel = client.post(
            "/api/channels", json={"name": "other-room"}, headers=headers
        ).json()

        # Try to reply to a message from the first channel, posted in the second channel
        resp = client.post(
            f"/api/channels/{other_channel['id']}/messages",
            json={"content": "Cross-channel reply attempt", "reply_to_id": message["id"]},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_reply_to_deleted_message_fails(self, client: TestClient, headers, channel, message):
        # Delete the original message
        del_resp = client.delete(f"/api/messages/{message['id']}", headers=headers)
        assert del_resp.status_code == 200

        # Try to reply to it
        resp = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "Reply to deleted", "reply_to_id": message["id"]},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_reply_appears_in_message_list(self, client: TestClient, headers, channel, message):
        client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "Reply in list", "reply_to_id": message["id"]},
            headers=headers,
        )
        resp = client.get(f"/api/channels/{channel['id']}/messages", headers=headers)
        assert resp.status_code == 200
        messages = resp.json()["messages"]
        replies = [m for m in messages if m["reply_to_id"] == message["id"]]
        assert len(replies) == 1
        assert replies[0]["reply_to"]["content"] == "Original message"

    def test_message_without_reply_to_has_null_fields(self, client: TestClient, headers, channel):
        resp = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "Plain message"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply_to_id"] is None
        assert data["reply_to"] is None
