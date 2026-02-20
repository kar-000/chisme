"""Tests for the GIF search + attach endpoints."""

import json

from fastapi.testclient import TestClient

from app.tests.conftest import auth_headers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenor_response(results: list | None = None) -> bytes:
    """Return minimal Tenor v2 JSON response bytes."""
    if results is None:
        results = [
            {
                "id": "123",
                "content_description": "funny dog",
                "media_formats": {
                    "tinygif": {
                        "url": "https://media.tenor.com/abc123/tinygif.gif",
                        "dims": [200, 150],
                    },
                    "nanogif": {
                        "url": "https://media.tenor.com/abc123/nanogif.gif",
                        "dims": [80, 60],
                    },
                },
            }
        ]
    return json.dumps({"results": results}).encode()


class _FakeResponse:
    """Minimal file-like object that mimics urllib HTTP response."""

    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGifSearch:
    def test_search_requires_auth(self, client: TestClient):
        resp = client.get("/api/gifs/search?q=dog")
        assert resp.status_code in (401, 403)

    def test_search_returns_gif_list(self, client: TestClient, monkeypatch):
        import urllib.request

        captured_url: list[str] = []

        def fake_urlopen(url, timeout=10):
            captured_url.append(url)
            return _FakeResponse(_make_tenor_response())

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

        headers = auth_headers(client)
        resp = client.get("/api/gifs/search?q=dog", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        gif = data[0]
        assert gif["id"] == "123"
        assert gif["url"] == "https://media.tenor.com/abc123/tinygif.gif"
        assert gif["preview_url"] == "https://media.tenor.com/abc123/nanogif.gif"
        assert gif["title"] == "funny dog"
        assert gif["width"] == 200
        assert gif["height"] == 150
        # Should have hit the search endpoint
        assert "search" in captured_url[0]
        assert "dog" in captured_url[0]

    def test_empty_query_uses_featured(self, client: TestClient, monkeypatch):
        import urllib.request

        captured_url: list[str] = []

        def fake_urlopen(url, timeout=10):
            captured_url.append(url)
            return _FakeResponse(_make_tenor_response())

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

        headers = auth_headers(client)
        resp = client.get("/api/gifs/search", headers=headers)
        assert resp.status_code == 200
        # Empty q → featured endpoint
        assert "featured" in captured_url[0]

    def test_limit_is_capped(self, client: TestClient, monkeypatch):
        import urllib.request
        import app.api.gifs as gifs_module

        captured_url: list[str] = []

        def fake_urlopen(url, timeout=10):
            captured_url.append(url)
            return _FakeResponse(_make_tenor_response([]))

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setattr(gifs_module.settings, "TENOR_SEARCH_LIMIT", 5)

        headers = auth_headers(client)
        resp = client.get("/api/gifs/search?q=cat&limit=100", headers=headers)
        assert resp.status_code == 200
        # The actual limit passed to Tenor should be capped at 5
        assert "limit=5" in captured_url[0]

    def test_search_skips_results_without_tinygif(self, client: TestClient, monkeypatch):
        import urllib.request

        raw = _make_tenor_response(
            [
                {
                    "id": "bad",
                    "content_description": "broken",
                    "media_formats": {},  # no tinygif
                },
                {
                    "id": "good",
                    "content_description": "ok",
                    "media_formats": {
                        "tinygif": {
                            "url": "https://media.tenor.com/good.gif",
                            "dims": [100, 100],
                        }
                    },
                },
            ]
        )

        monkeypatch.setattr(urllib.request, "urlopen", lambda url, timeout=10: _FakeResponse(raw))

        headers = auth_headers(client)
        resp = client.get("/api/gifs/search?q=test", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # Only the "good" result with a tinygif should appear
        assert len(data) == 1
        assert data[0]["id"] == "good"


class TestGifAttach:
    def test_attach_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/gifs/attach",
            json={"tenor_id": "123", "url": "https://media.tenor.com/abc.gif"},
        )
        assert resp.status_code in (401, 403)

    def test_attach_creates_attachment_row(self, client: TestClient):
        headers = auth_headers(client)
        tenor_url = "https://media.tenor.com/abc123_tinygif.gif"
        resp = client.post(
            "/api/gifs/attach",
            json={
                "tenor_id": "abc123",
                "url": tenor_url,
                "title": "funny dog",
                "width": 200,
                "height": 150,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == tenor_url  # external_url takes precedence
        assert data["mime_type"] == "image/gif"
        assert data["size"] == 0
        assert "id" in data
        assert data["original_filename"] == "funny dog"

    def test_attach_without_title_uses_tenor_id(self, client: TestClient):
        headers = auth_headers(client)
        tenor_url = "https://media.tenor.com/xyz_tinygif.gif"
        resp = client.post(
            "/api/gifs/attach",
            json={"tenor_id": "xyz", "url": tenor_url},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # original_filename falls back to tenor_{id}.gif when title is empty
        assert data["original_filename"] == "tenor_xyz.gif"

    def test_attach_then_send_message(self, client: TestClient):
        headers = auth_headers(client)

        # Create channel
        channel = client.post(
            "/api/channels", json={"name": "gif-room"}, headers=headers
        ).json()

        # Attach GIF
        gif_url = "https://media.tenor.com/sendable.gif"
        att = client.post(
            "/api/gifs/attach",
            json={"tenor_id": "send1", "url": gif_url, "title": "wave"},
            headers=headers,
        ).json()

        # Send message with GIF attachment
        resp = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "", "attachment_ids": [att["id"]]},
            headers=headers,
        )
        assert resp.status_code == 200
        msg = resp.json()
        assert len(msg["attachments"]) == 1
        assert msg["attachments"][0]["url"] == gif_url
        assert msg["attachments"][0]["mime_type"] == "image/gif"
