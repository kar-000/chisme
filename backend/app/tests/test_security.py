"""Security validation tests — authorization boundaries."""

from fastapi.testclient import TestClient

from app.tests.conftest import auth_headers


def make_second_user(client):
    return auth_headers(client, username="other", email="other@example.com", password="OtherPass1!")


class TestAuthorizationBoundaries:
    def test_edit_others_message_forbidden(self, client: TestClient):
        headers1 = auth_headers(client)
        channel_resp = client.post("/api/channels", json={"name": "sec-room"}, headers=headers1)
        channel_id = channel_resp.json()["id"]

        msg_resp = client.post(
            f"/api/channels/{channel_id}/messages",
            json={"content": "owner's message"},
            headers=headers1,
        )
        msg_id = msg_resp.json()["id"]

        headers2 = make_second_user(client)
        resp = client.put(f"/api/messages/{msg_id}", json={"content": "hacked!"}, headers=headers2)
        assert resp.status_code == 403

    def test_delete_others_message_forbidden(self, client: TestClient):
        headers1 = auth_headers(client)
        channel_resp = client.post("/api/channels", json={"name": "sec-room2"}, headers=headers1)
        channel_id = channel_resp.json()["id"]

        msg_resp = client.post(
            f"/api/channels/{channel_id}/messages",
            json={"content": "owner's message"},
            headers=headers1,
        )
        msg_id = msg_resp.json()["id"]

        headers2 = make_second_user(client)
        resp = client.delete(f"/api/messages/{msg_id}", headers=headers2)
        assert resp.status_code == 403

    def test_expired_token_rejected(self, client: TestClient):
        from datetime import timedelta

        from app.core.security import create_access_token

        # Create a token that expired in the past; jose raises JWTError → 401
        token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_tampered_token_rejected(self, client: TestClient):
        headers = auth_headers(client)
        bad_token = headers["Authorization"].replace("Bearer ", "") + "tampered"
        # Invalid JWT signature → jose raises JWTError → 401
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
        assert resp.status_code == 401
