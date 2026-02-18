"""Tests for file upload endpoint and attachment behaviour."""

import io
import pytest
from fastapi.testclient import TestClient

from app.tests.conftest import auth_headers


class TestUploadEndpoint:
    def test_upload_image_success(self, client: TestClient):
        headers = auth_headers(client)
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        resp = client.post(
            "/api/upload",
            files={"file": ("test.png", io.BytesIO(png_bytes), "image/png")},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["original_filename"] == "test.png"
        assert data["mime_type"] == "image/png"
        assert data["url"].startswith("/uploads/")
        assert "id" in data

    def test_upload_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/upload",
            files={"file": ("test.png", io.BytesIO(b"data"), "image/png")},
        )
        assert resp.status_code in (401, 403)

    def test_upload_disallowed_type_returns_415(self, client: TestClient):
        headers = auth_headers(client)
        resp = client.post(
            "/api/upload",
            files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
            headers=headers,
        )
        assert resp.status_code == 415

    def test_upload_oversized_file_returns_413(self, client: TestClient, monkeypatch):
        import app.api.uploads as uploads_module
        monkeypatch.setattr(uploads_module.settings, "MAX_UPLOAD_SIZE", 10)
        headers = auth_headers(client)
        resp = client.post(
            "/api/upload",
            files={"file": ("big.png", io.BytesIO(b"X" * 20), "image/png")},
            headers=headers,
        )
        assert resp.status_code == 413

    def test_upload_returns_unique_filenames(self, client: TestClient):
        headers = auth_headers(client)
        payload = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

        r1 = client.post(
            "/api/upload",
            files={"file": ("a.png", io.BytesIO(payload), "image/png")},
            headers=headers,
        )
        r2 = client.post(
            "/api/upload",
            files={"file": ("a.png", io.BytesIO(payload), "image/png")},
            headers=headers,
        )
        assert r1.json()["filename"] != r2.json()["filename"]


class TestAttachmentInMessages:
    def _make_channel(self, client, headers):
        return client.post("/api/channels", json={"name": "media-room"}, headers=headers).json()

    def _upload(self, client, headers):
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        return client.post(
            "/api/upload",
            files={"file": ("img.png", io.BytesIO(png), "image/png")},
            headers=headers,
        ).json()

    def test_send_message_with_attachment(self, client: TestClient):
        headers = auth_headers(client)
        channel = self._make_channel(client, headers)
        att = self._upload(client, headers)

        resp = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "look at this", "attachment_ids": [att["id"]]},
            headers=headers,
        )
        assert resp.status_code == 200
        msg = resp.json()
        assert len(msg["attachments"]) == 1
        assert msg["attachments"][0]["id"] == att["id"]
        assert msg["attachments"][0]["url"].startswith("/uploads/")

    def test_send_attachment_only_no_text(self, client: TestClient):
        headers = auth_headers(client)
        channel = self._make_channel(client, headers)
        att = self._upload(client, headers)

        resp = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "", "attachment_ids": [att["id"]]},
            headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()["attachments"]) == 1

    def test_send_empty_message_no_attachment_still_fails(self, client: TestClient):
        headers = auth_headers(client)
        channel = self._make_channel(client, headers)
        resp = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "", "attachment_ids": []},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_cannot_steal_others_attachment(self, client: TestClient):
        """User B cannot attach a file uploaded by User A."""
        headers_a = auth_headers(client, username="alice", email="alice@x.com")
        headers_b = auth_headers(client, username="bob", email="bob@x.com", password="BobPass1!")
        channel = self._make_channel(client, headers_a)
        att = self._upload(client, headers_a)

        resp = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "mine now", "attachment_ids": [att["id"]]},
            headers=headers_b,
        )
        # Bob's message sends fine, but the attachment (owned by Alice) is not linked
        assert resp.status_code == 200
        assert resp.json()["attachments"] == []

    def test_attachments_in_message_list(self, client: TestClient):
        headers = auth_headers(client)
        channel = self._make_channel(client, headers)
        att = self._upload(client, headers)
        client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "img", "attachment_ids": [att["id"]]},
            headers=headers,
        )

        resp = client.get(f"/api/channels/{channel['id']}/messages", headers=headers)
        assert resp.status_code == 200
        msgs = resp.json()["messages"]
        assert len(msgs[0]["attachments"]) == 1

    def test_delete_message_hides_attachments(self, client: TestClient):
        """Soft-deleting a message removes it (and its attachments) from the feed."""
        headers = auth_headers(client)
        channel = self._make_channel(client, headers)
        att = self._upload(client, headers)

        msg_resp = client.post(
            f"/api/channels/{channel['id']}/messages",
            json={"content": "bye", "attachment_ids": [att["id"]]},
            headers=headers,
        )
        msg_id = msg_resp.json()["id"]

        del_resp = client.delete(f"/api/messages/{msg_id}", headers=headers)
        assert del_resp.status_code == 200

        # Soft-deleted messages no longer appear in the channel feed
        feed = client.get(f"/api/channels/{channel['id']}/messages", headers=headers).json()
        msg_ids_in_feed = [m["id"] for m in feed["messages"]]
        assert msg_id not in msg_ids_in_feed
