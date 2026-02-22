"""
Tests for:
  - GET /api/search/messages
  - GET /api/users/{user_id}  (profile read)
  - PATCH /api/users/me       (profile update: display_name, bio, status)
"""

from app.tests.conftest import auth_headers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_channel(client, headers, name="testchan"):
    r = client.post("/api/channels", json={"name": name}, headers=headers)
    assert r.status_code == 200
    return r.json()["id"]


def _post_message(client, headers, channel_id, content):
    r = client.post(
        f"/api/channels/{channel_id}/messages",
        json={"content": content},
        headers=headers,
    )
    assert r.status_code == 200
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Search tests
# ---------------------------------------------------------------------------


class TestMessageSearch:
    def test_search_requires_auth(self, client):
        r = client.get("/api/search/messages?q=hello")
        assert r.status_code in (401, 403)

    def test_search_returns_matching_messages(self, client):
        hdrs = auth_headers(client)
        ch = _make_channel(client, hdrs)
        _post_message(client, hdrs, ch, "hello world")
        _post_message(client, hdrs, ch, "goodbye world")

        r = client.get("/api/search/messages?q=hello", headers=hdrs)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["results"][0]["content"] == "hello world"

    def test_search_case_insensitive(self, client):
        hdrs = auth_headers(client)
        ch = _make_channel(client, hdrs)
        _post_message(client, hdrs, ch, "Hello World")

        r = client.get("/api/search/messages?q=hello", headers=hdrs)
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_search_filter_by_channel(self, client):
        hdrs = auth_headers(client)
        ch1 = _make_channel(client, hdrs, "chan1")
        ch2 = _make_channel(client, hdrs, "chan2")
        _post_message(client, hdrs, ch1, "needle in channel 1")
        _post_message(client, hdrs, ch2, "needle in channel 2")

        r = client.get(f"/api/search/messages?q=needle&channel_id={ch1}", headers=hdrs)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["results"][0]["channel_id"] == ch1

    def test_search_no_results(self, client):
        hdrs = auth_headers(client)
        ch = _make_channel(client, hdrs)
        _post_message(client, hdrs, ch, "hello world")

        r = client.get("/api/search/messages?q=zzznomatch", headers=hdrs)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_search_blank_query_rejected(self, client):
        hdrs = auth_headers(client)
        r = client.get("/api/search/messages?q=   ", headers=hdrs)
        assert r.status_code == 422

    def test_search_includes_channel_name(self, client):
        hdrs = auth_headers(client)
        ch = _make_channel(client, hdrs, "mychannel")
        _post_message(client, hdrs, ch, "unique phrase")

        r = client.get("/api/search/messages?q=unique+phrase", headers=hdrs)
        assert r.status_code == 200
        result = r.json()["results"][0]
        assert result["channel_name"] == "mychannel"

    def test_search_deleted_messages_excluded(self, client):
        hdrs = auth_headers(client)
        ch = _make_channel(client, hdrs)
        msg_id = _post_message(client, hdrs, ch, "to be deleted")

        client.delete(f"/api/messages/{msg_id}", headers=hdrs)

        r = client.get("/api/search/messages?q=to+be+deleted", headers=hdrs)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_search_limit_enforced(self, client):
        hdrs = auth_headers(client)
        ch = _make_channel(client, hdrs)
        for i in range(5):
            _post_message(client, hdrs, ch, f"repeated msg {i}")

        r = client.get("/api/search/messages?q=repeated+msg&limit=3", headers=hdrs)
        assert r.status_code == 200
        assert r.json()["total"] == 3


# ---------------------------------------------------------------------------
# Profile tests
# ---------------------------------------------------------------------------


class TestUserProfile:
    def test_get_profile_by_id(self, client):
        hdrs = auth_headers(client)
        # Get own ID from /api/auth/me
        me_r = client.get("/api/auth/me", headers=hdrs)
        assert me_r.status_code == 200
        user_id = me_r.json()["id"]

        r = client.get(f"/api/users/{user_id}", headers=hdrs)
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "testuser"
        assert "bio" in data
        assert "display_name" in data

    def test_get_profile_404(self, client):
        hdrs = auth_headers(client)
        r = client.get("/api/users/99999", headers=hdrs)
        assert r.status_code == 404

    def test_patch_display_name(self, client):
        hdrs = auth_headers(client)
        r = client.patch("/api/users/me", json={"display_name": "Cool Name"}, headers=hdrs)
        assert r.status_code == 200
        assert r.json()["display_name"] == "Cool Name"

    def test_patch_bio(self, client):
        hdrs = auth_headers(client)
        r = client.patch("/api/users/me", json={"bio": "I love chisme"}, headers=hdrs)
        assert r.status_code == 200
        assert r.json()["bio"] == "I love chisme"

    def test_patch_status(self, client):
        hdrs = auth_headers(client)
        r = client.patch("/api/users/me", json={"status": "away"}, headers=hdrs)
        assert r.status_code == 200
        assert r.json()["status"] == "away"

    def test_patch_multiple_fields(self, client):
        hdrs = auth_headers(client)
        r = client.patch(
            "/api/users/me",
            json={"display_name": "MyName", "bio": "My bio", "status": "dnd"},
            headers=hdrs,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["display_name"] == "MyName"
        assert data["bio"] == "My bio"
        assert data["status"] == "dnd"

    def test_patch_display_name_too_long(self, client):
        hdrs = auth_headers(client)
        r = client.patch("/api/users/me", json={"display_name": "x" * 51}, headers=hdrs)
        assert r.status_code == 422

    def test_patch_bio_too_long(self, client):
        hdrs = auth_headers(client)
        r = client.patch("/api/users/me", json={"bio": "x" * 501}, headers=hdrs)
        assert r.status_code == 422

    def test_patch_requires_auth(self, client):
        r = client.patch("/api/users/me", json={"bio": "nope"})
        assert r.status_code in (401, 403)

    def test_display_name_null_clears_it(self, client):
        hdrs = auth_headers(client)
        client.patch("/api/users/me", json={"display_name": "Old Name"}, headers=hdrs)
        r = client.patch("/api/users/me", json={"display_name": None}, headers=hdrs)
        assert r.status_code == 200
        assert r.json()["display_name"] is None
