"""Tests for WebSocket channel and DM endpoints.

Covers the accept-then-authenticate flow introduced to fix the
Starlette 0.41 requirement that websocket.accept() must be called
before receive_text().
"""

import pytest
from fastapi.testclient import TestClient

from app.tests.conftest import register_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register(client: TestClient, username: str, email: str, password: str = "Password1!") -> dict:
    resp = register_user(client, username=username, email=email, password=password)
    assert resp.status_code == 200, resp.json()
    return resp.json()  # {"access_token": ..., "user": {...}}


def _make_channel(client: TestClient, headers: dict, name: str = "ws-room") -> int:
    resp = client.post("/api/channels", json={"name": name}, headers=headers)
    assert resp.status_code == 200
    return resp.json()["id"]


def _make_dm(client: TestClient, token: str, other_user_id: int) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(f"/api/dms?other_user_id={other_user_id}", headers=headers)
    assert resp.status_code == 200
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Channel WebSocket
# ---------------------------------------------------------------------------

class TestChannelWebSocket:
    def test_connect_and_auth_succeeds(self, client: TestClient):
        """WebSocket upgrades (101) and accepts a valid auth message."""
        data = _register(client, "wsuser", "ws@example.com")
        token = data["access_token"]
        channel_id = _make_channel(client, {"Authorization": f"Bearer {token}"})

        with client.websocket_connect(f"/ws/channels/{channel_id}") as ws:
            ws.send_json({"type": "auth", "token": token})
            event = ws.receive_json()
            assert event["type"] == "user.joined"

    def test_connect_rejects_bad_token(self, client: TestClient):
        """WebSocket closes with 1008 when an invalid token is sent."""
        data = _register(client, "wsreject", "wsreject@example.com")
        token = data["access_token"]
        channel_id = _make_channel(client, {"Authorization": f"Bearer {token}"})

        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/channels/{channel_id}") as ws:
                ws.send_json({"type": "auth", "token": "not-a-real-token"})
                ws.receive_json()  # server closes → raises

    def test_connect_rejects_wrong_message_type(self, client: TestClient):
        """WebSocket closes with 1008 when first message is not type=auth."""
        data = _register(client, "wswrong", "wswrong@example.com")
        token = data["access_token"]
        channel_id = _make_channel(client, {"Authorization": f"Bearer {token}"})

        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/channels/{channel_id}") as ws:
                ws.send_json({"type": "hello", "token": token})
                ws.receive_json()

    def test_typing_event_broadcast(self, client: TestClient):
        """user.typing sent by one client is broadcast to others on the channel."""
        data1 = _register(client, "typer1", "typer1@example.com")
        data2 = _register(client, "typer2", "typer2@example.com")
        token1, token2 = data1["access_token"], data2["access_token"]
        channel_id = _make_channel(client, {"Authorization": f"Bearer {token1}"}, name="typing-room")

        with client.websocket_connect(f"/ws/channels/{channel_id}") as ws1:
            ws1.send_json({"type": "auth", "token": token1})
            ws1.receive_json()  # ws1's user.joined

            with client.websocket_connect(f"/ws/channels/{channel_id}") as ws2:
                ws2.send_json({"type": "auth", "token": token2})
                ws1.receive_json()  # ws1 sees ws2 join
                ws2.receive_json()  # ws2 sees its own join

                ws2.send_json({"type": "user.typing"})

                event = ws1.receive_json()
                assert event["type"] == "user.typing"
                assert event["username"] == "typer2"


# ---------------------------------------------------------------------------
# DM WebSocket
# ---------------------------------------------------------------------------

class TestDMWebSocket:
    def test_dm_connect_and_auth_succeeds(self, client: TestClient):
        """DM WebSocket upgrades and accepts a valid auth message."""
        data1 = _register(client, "dmuser1", "dmuser1@example.com")
        data2 = _register(client, "dmuser2", "dmuser2@example.com")
        token1 = data1["access_token"]
        user2_id = data2["user"]["id"]
        dm_id = _make_dm(client, token1, user2_id)

        with client.websocket_connect(f"/ws/dm/{dm_id}") as ws:
            ws.send_json({"type": "auth", "token": token1})
            # DM handler has no broadcast on join — connection just stays open

    def test_dm_rejects_non_participant(self, client: TestClient):
        """DM WebSocket closes with 1008 for a user not in the DM."""
        data1 = _register(client, "dmparta", "dmparta@example.com")
        data2 = _register(client, "dmpartb", "dmpartb@example.com")
        data3 = _register(client, "dmpartc", "dmpartc@example.com")
        token1 = data1["access_token"]
        token3 = data3["access_token"]
        user2_id = data2["user"]["id"]
        dm_id = _make_dm(client, token1, user2_id)

        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/dm/{dm_id}") as ws:
                ws.send_json({"type": "auth", "token": token3})  # not a participant
                ws.receive_json()

    def test_dm_rejects_bad_token(self, client: TestClient):
        """DM WebSocket closes with 1008 for an invalid token."""
        data1 = _register(client, "dmtokx", "dmtokx@example.com")
        data2 = _register(client, "dmtoky", "dmtoky@example.com")
        token1 = data1["access_token"]
        user2_id = data2["user"]["id"]
        dm_id = _make_dm(client, token1, user2_id)

        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/dm/{dm_id}") as ws:
                ws.send_json({"type": "auth", "token": "garbage"})
                ws.receive_json()
