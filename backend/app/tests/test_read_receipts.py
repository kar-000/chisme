"""
Tests for the read receipt system (unread count tracking).

Covers:
  - GET /api/channels includes unread_count per channel
  - POST /api/channels/{id}/read marks messages as read
  - Unread count resets to 0 after marking read
  - New messages posted after marking read show as unread
  - Never-read channel shows all messages as unread
  - Requires authentication
"""

import pytest
from fastapi.testclient import TestClient

from app.tests.conftest import auth_headers


def _register(client, username, email, password="Password1!"):
    resp = client.post("/api/auth/register", json={"username": username, "email": email, "password": password})
    assert resp.status_code == 200, resp.json()
    return resp.json()


def _make_channel(client, headers, name):
    resp = client.post("/api/channels", json={"name": name}, headers=headers)
    assert resp.status_code == 200, resp.json()
    return resp.json()["id"]


def _send(client, headers, channel_id, content):
    resp = client.post(f"/api/channels/{channel_id}/messages", json={"content": content}, headers=headers)
    assert resp.status_code == 200, resp.json()
    return resp.json()


# ---------------------------------------------------------------------------
# GET /api/channels — unread_count field
# ---------------------------------------------------------------------------

class TestUnreadCountInChannelList:
    def test_channel_list_includes_unread_count(self, client: TestClient):
        """Channel list response always has unread_count field."""
        h = auth_headers(client, username="rr_list1", email="rr_list1@x.com")
        _make_channel(client, h, "rr-list1")
        resp = client.get("/api/channels", headers=h)
        assert resp.status_code == 200
        for ch in resp.json():
            assert "unread_count" in ch

    def test_new_channel_has_zero_unread(self, client: TestClient):
        """A channel with no messages has unread_count == 0."""
        h = auth_headers(client, username="rr_zero1", email="rr_zero1@x.com")
        ch_id = _make_channel(client, h, "rr-zero1")
        resp = client.get("/api/channels", headers=h)
        channel = next(c for c in resp.json() if c["id"] == ch_id)
        assert channel["unread_count"] == 0

    def test_messages_before_first_visit_are_unread(self, client: TestClient):
        """Messages sent before a user ever opens a channel count as unread."""
        h1 = auth_headers(client, username="rr_sender1", email="rr_sender1@x.com")
        data2 = _register(client, "rr_reader1", "rr_reader1@x.com")
        h2 = {"Authorization": f"Bearer {data2['access_token']}"}

        ch_id = _make_channel(client, h1, "rr-unread1")
        _send(client, h1, ch_id, "hello")
        _send(client, h1, ch_id, "world")

        resp = client.get("/api/channels", headers=h2)
        channel = next((c for c in resp.json() if c["id"] == ch_id), None)
        # Channel may not appear if private; here it's public so it should
        if channel:
            assert channel["unread_count"] == 2

    def test_requires_auth(self, client: TestClient):
        resp = client.get("/api/channels")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/channels/{id}/read
# ---------------------------------------------------------------------------

class TestMarkChannelRead:
    def test_mark_read_returns_204(self, client: TestClient):
        h = auth_headers(client, username="rr_mark1", email="rr_mark1@x.com")
        ch_id = _make_channel(client, h, "rr-mark1")
        _send(client, h, ch_id, "a message")
        resp = client.post(f"/api/channels/{ch_id}/read", headers=h)
        assert resp.status_code == 204

    def test_mark_read_clears_unread_count(self, client: TestClient):
        """After marking read, the channel's unread_count drops to 0."""
        h = auth_headers(client, username="rr_clear1", email="rr_clear1@x.com")
        ch_id = _make_channel(client, h, "rr-clear1")
        _send(client, h, ch_id, "msg 1")
        _send(client, h, ch_id, "msg 2")

        # Verify unread first
        before = client.get("/api/channels", headers=h)
        ch_before = next(c for c in before.json() if c["id"] == ch_id)
        assert ch_before["unread_count"] == 2

        # Mark as read
        client.post(f"/api/channels/{ch_id}/read", headers=h)

        # Verify cleared
        after = client.get("/api/channels", headers=h)
        ch_after = next(c for c in after.json() if c["id"] == ch_id)
        assert ch_after["unread_count"] == 0

    def test_new_messages_after_read_are_unread(self, client: TestClient):
        """Messages sent after marking read count as unread again."""
        h = auth_headers(client, username="rr_new1", email="rr_new1@x.com")
        ch_id = _make_channel(client, h, "rr-new1")
        _send(client, h, ch_id, "old message")
        client.post(f"/api/channels/{ch_id}/read", headers=h)

        _send(client, h, ch_id, "new message 1")
        _send(client, h, ch_id, "new message 2")

        resp = client.get("/api/channels", headers=h)
        ch = next(c for c in resp.json() if c["id"] == ch_id)
        assert ch["unread_count"] == 2

    def test_mark_read_idempotent(self, client: TestClient):
        """Calling mark-read multiple times doesn't break anything."""
        h = auth_headers(client, username="rr_idem1", email="rr_idem1@x.com")
        ch_id = _make_channel(client, h, "rr-idem1")
        _send(client, h, ch_id, "a")
        client.post(f"/api/channels/{ch_id}/read", headers=h)
        client.post(f"/api/channels/{ch_id}/read", headers=h)
        resp = client.get("/api/channels", headers=h)
        ch = next(c for c in resp.json() if c["id"] == ch_id)
        assert ch["unread_count"] == 0

    def test_mark_read_channel_not_found(self, client: TestClient):
        h = auth_headers(client, username="rr_404", email="rr_404@x.com")
        resp = client.post("/api/channels/99999/read", headers=h)
        assert resp.status_code == 404

    def test_mark_read_requires_auth(self, client: TestClient):
        h = auth_headers(client, username="rr_auth1", email="rr_auth1@x.com")
        ch_id = _make_channel(client, h, "rr-auth1")
        resp = client.post(f"/api/channels/{ch_id}/read")
        assert resp.status_code in (401, 403)

    def test_mark_read_empty_channel(self, client: TestClient):
        """Marking an empty channel as read (no messages) doesn't error."""
        h = auth_headers(client, username="rr_empty1", email="rr_empty1@x.com")
        ch_id = _make_channel(client, h, "rr-empty1")
        resp = client.post(f"/api/channels/{ch_id}/read", headers=h)
        assert resp.status_code == 204

    def test_different_users_have_independent_unread_counts(self, client: TestClient):
        """User A reading doesn't affect user B's unread count."""
        d1 = _register(client, "rr_ind1a", "rr_ind1a@x.com")
        d2 = _register(client, "rr_ind1b", "rr_ind1b@x.com")
        h1 = {"Authorization": f"Bearer {d1['access_token']}"}
        h2 = {"Authorization": f"Bearer {d2['access_token']}"}

        ch_id = _make_channel(client, h1, "rr-ind1")
        _send(client, h1, ch_id, "hello from user1")

        # user1 marks read
        client.post(f"/api/channels/{ch_id}/read", headers=h1)

        # user1 sees 0 unread
        r1 = client.get("/api/channels", headers=h1)
        ch1 = next(c for c in r1.json() if c["id"] == ch_id)
        assert ch1["unread_count"] == 0

        # user2 still sees 1 unread
        r2 = client.get("/api/channels", headers=h2)
        ch2 = next(c for c in r2.json() if c["id"] == ch_id)
        assert ch2["unread_count"] == 1
