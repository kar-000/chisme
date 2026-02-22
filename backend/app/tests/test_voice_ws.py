"""
WebSocket voice signaling tests.

Covers the /ws/voice endpoint (global, server-wide voice channel):
  - voice.join broadcasts voice.user_joined to all connected clients
  - voice.leave broadcasts voice.user_left
  - voice.offer / voice.answer / voice.ice_candidate relayed to target user
  - Auto-leave on disconnect broadcasts voice.user_left (no channel events)
  - Signaling to non-voice target is silently dropped
  - Signaling with non-integer target_id is silently dropped
  - voice.state_snapshot always sent on connect (empty list when voice is empty)
"""

from fastapi.testclient import TestClient

from app.tests.conftest import register_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register(client: TestClient, username: str, email: str, password: str = "Password1!") -> dict:
    resp = register_user(client, username=username, email=email, password=password)
    assert resp.status_code == 200, resp.json()
    return resp.json()  # {"access_token": ..., "user": {...}}


def _auth_voice_ws(ws, token: str) -> dict:
    """Send auth and receive the immediate voice.state_snapshot response.

    The /ws/voice endpoint always sends a snapshot right after auth,
    even when no users are in voice (users list will be []).
    """
    ws.send_json({"type": "auth", "token": token})
    snapshot = ws.receive_json()
    assert snapshot["type"] == "voice.state_snapshot", snapshot
    return snapshot


# ---------------------------------------------------------------------------
# Voice join / leave
# ---------------------------------------------------------------------------


class TestVoiceJoinLeave:
    def test_voice_join_broadcasts_user_joined(self, client: TestClient):
        """voice.join from user1 → voice.user_joined broadcast received by user2."""
        d1 = _register(client, "vj1a", "vj1a@x.com")
        d2 = _register(client, "vj1b", "vj1b@x.com")

        with client.websocket_connect("/ws/voice") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect("/ws/voice") as ws2:
                _auth_voice_ws(ws2, d2["access_token"])

                ws1.send_json({"type": "voice.join", "muted": False, "video": False})

                # Broadcast has no exclude — both clients receive voice.user_joined
                ws1.receive_json()  # own broadcast
                event = ws2.receive_json()
                assert event["type"] == "voice.user_joined"
                assert event["user_id"] == d1["user"]["id"]
                assert event["muted"] is False

    def test_voice_leave_broadcasts_user_left(self, client: TestClient):
        """voice.leave from user1 → voice.user_left broadcast received by user2."""
        d1 = _register(client, "vl1a", "vl1a@x.com")
        d2 = _register(client, "vl1b", "vl1b@x.com")

        with client.websocket_connect("/ws/voice") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect("/ws/voice") as ws2:
                _auth_voice_ws(ws2, d2["access_token"])

                ws1.send_json({"type": "voice.join", "muted": True, "video": False})
                ws1.receive_json()  # own voice.user_joined
                ws2.receive_json()  # voice.user_joined for ws1

                ws1.send_json({"type": "voice.leave"})

                event = ws2.receive_json()
                assert event["type"] == "voice.user_left"
                assert event["user_id"] == d1["user"]["id"]

    def test_voice_disconnect_auto_leave(self, client: TestClient):
        """Closing WS while in voice → voice.user_left broadcast to remaining users.

        Unlike the channel WS, /ws/voice disconnect emits only voice.user_left —
        no user.left or presence.changed events on the voice endpoint.
        """
        d1 = _register(client, "vd1a", "vd1a@x.com")
        d2 = _register(client, "vd1b", "vd1b@x.com")

        with client.websocket_connect("/ws/voice") as ws2:
            _auth_voice_ws(ws2, d2["access_token"])

            with client.websocket_connect("/ws/voice") as ws1:
                _auth_voice_ws(ws1, d1["access_token"])

                ws1.send_json({"type": "voice.join", "muted": False, "video": False})
                ws1.receive_json()  # own voice.user_joined
                ws2.receive_json()  # voice.user_joined for ws1

            # ws1 context exits — connection closed while in voice.
            # ws2 should receive exactly one event: voice.user_left.
            event = ws2.receive_json()
            assert event["type"] == "voice.user_left"
            assert event["user_id"] == d1["user"]["id"]


# ---------------------------------------------------------------------------
# Voice signaling relay
# ---------------------------------------------------------------------------


class TestVoiceSignalingRelay:
    def _two_users(self, client: TestClient, prefix: str):
        """Register two users and return their auth dicts."""
        d1 = _register(client, f"{prefix}u1", f"{prefix}u1@x.com")
        d2 = _register(client, f"{prefix}u2", f"{prefix}u2@x.com")
        return d1, d2

    def test_voice_offer_relayed_to_target(self, client: TestClient):
        """voice.offer from user1 targeting user2 is delivered to user2."""
        d1, d2 = self._two_users(client, "offer")

        with client.websocket_connect("/ws/voice") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect("/ws/voice") as ws2:
                _auth_voice_ws(ws2, d2["access_token"])

                # Both join voice
                ws1.send_json({"type": "voice.join", "muted": False, "video": False})
                ws1.receive_json()  # own voice.user_joined
                ws2.receive_json()  # ws2 sees ws1 join

                ws2.send_json({"type": "voice.join", "muted": True, "video": False})
                ws1.receive_json()  # ws1 sees ws2 join
                ws2.receive_json()  # own voice.user_joined

                # user1 sends offer to user2
                ws1.send_json(
                    {
                        "type": "voice.offer",
                        "target_user_id": d2["user"]["id"],
                        "sdp": {"type": "offer", "sdp": "fake-sdp"},
                    }
                )

                event = ws2.receive_json()
                assert event["type"] == "voice.offer"
                assert event["from_user_id"] == d1["user"]["id"]
                assert event["sdp"]["type"] == "offer"

    def test_voice_answer_relayed_to_target(self, client: TestClient):
        """voice.answer from user2 targeting user1 is delivered to user1."""
        d1, d2 = self._two_users(client, "answer")

        with client.websocket_connect("/ws/voice") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect("/ws/voice") as ws2:
                _auth_voice_ws(ws2, d2["access_token"])

                ws1.send_json({"type": "voice.join", "muted": False, "video": False})
                ws1.receive_json()
                ws2.receive_json()

                ws2.send_json({"type": "voice.join", "muted": True, "video": False})
                ws1.receive_json()
                ws2.receive_json()

                ws2.send_json(
                    {
                        "type": "voice.answer",
                        "target_user_id": d1["user"]["id"],
                        "sdp": {"type": "answer", "sdp": "fake-answer"},
                    }
                )

                event = ws1.receive_json()
                assert event["type"] == "voice.answer"
                assert event["from_user_id"] == d2["user"]["id"]

    def test_voice_ice_candidate_relayed_to_target(self, client: TestClient):
        """voice.ice_candidate from user1 targeting user2 is delivered to user2."""
        d1, d2 = self._two_users(client, "ice")

        with client.websocket_connect("/ws/voice") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect("/ws/voice") as ws2:
                _auth_voice_ws(ws2, d2["access_token"])

                ws1.send_json({"type": "voice.join", "muted": False, "video": False})
                ws1.receive_json()
                ws2.receive_json()

                ws2.send_json({"type": "voice.join", "muted": True, "video": False})
                ws1.receive_json()
                ws2.receive_json()

                ws1.send_json(
                    {
                        "type": "voice.ice_candidate",
                        "target_user_id": d2["user"]["id"],
                        "candidate": {"candidate": "candidate:1 udp ...", "sdpMid": "0"},
                    }
                )

                event = ws2.receive_json()
                assert event["type"] == "voice.ice_candidate"
                assert event["from_user_id"] == d1["user"]["id"]
                assert event["candidate"]["sdpMid"] == "0"

    def test_offer_to_non_voice_target_is_dropped(self, client: TestClient):
        """voice.offer with a target not in voice is silently dropped.

        Sentinel: after the dropped offer, ws1 sends voice.leave.
        ws2's next message must be voice.user_left, not voice.offer.
        """
        d1, d2 = self._two_users(client, "drop")

        with client.websocket_connect("/ws/voice") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect("/ws/voice") as ws2:
                _auth_voice_ws(ws2, d2["access_token"])

                # Only ws1 joins voice; ws2 does NOT join
                ws1.send_json({"type": "voice.join", "muted": False, "video": False})
                ws1.receive_json()  # own voice.user_joined
                ws2.receive_json()  # voice.user_joined for ws1

                # ws1 tries to signal ws2 who is not in voice → should be dropped
                ws1.send_json(
                    {
                        "type": "voice.offer",
                        "target_user_id": d2["user"]["id"],
                        "sdp": {"type": "offer", "sdp": "fake"},
                    }
                )

                # Sentinel: ws1 leaves → ws2 next message must be voice.user_left
                ws1.send_json({"type": "voice.leave"})
                sentinel = ws2.receive_json()
                assert sentinel["type"] == "voice.user_left"

    def test_offer_with_string_target_id_is_dropped(self, client: TestClient):
        """voice.offer with a non-integer target_user_id is silently dropped."""
        d1, d2 = self._two_users(client, "strid")

        with client.websocket_connect("/ws/voice") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect("/ws/voice") as ws2:
                _auth_voice_ws(ws2, d2["access_token"])

                ws1.send_json({"type": "voice.join", "muted": False, "video": False})
                ws1.receive_json()
                ws2.receive_json()

                ws2.send_json({"type": "voice.join", "muted": True, "video": False})
                ws1.receive_json()
                ws2.receive_json()

                # String target_id — should be dropped
                ws1.send_json(
                    {
                        "type": "voice.offer",
                        "target_user_id": str(d2["user"]["id"]),  # string, not int
                        "sdp": {"type": "offer", "sdp": "fake"},
                    }
                )

                # Sentinel: ws1 leaves → ws2 next message must be voice.user_left
                ws1.send_json({"type": "voice.leave"})
                sentinel = ws2.receive_json()
                assert sentinel["type"] == "voice.user_left"


# ---------------------------------------------------------------------------
# Voice state snapshot
# ---------------------------------------------------------------------------


class TestVoiceStateSnapshot:
    def test_snapshot_sent_when_voice_occupied(self, client: TestClient):
        """New /ws/voice connection receives voice.state_snapshot with current participants."""
        d1 = _register(client, "snap1a", "snap1a@x.com")
        d2 = _register(client, "snap1b", "snap1b@x.com")

        with client.websocket_connect("/ws/voice") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])
            ws1.send_json({"type": "voice.join", "muted": True, "video": False})
            ws1.receive_json()  # own voice.user_joined broadcast

            with client.websocket_connect("/ws/voice") as ws2:
                # Snapshot is the first message after auth — should include d1
                snapshot = _auth_voice_ws(ws2, d2["access_token"])
                user_ids = [u["user_id"] for u in snapshot["users"]]
                assert d1["user"]["id"] in user_ids

    def test_snapshot_sent_even_when_voice_empty(self, client: TestClient):
        """New /ws/voice connection receives voice.state_snapshot with users=[] when empty."""
        d1 = _register(client, "snap2a", "snap2a@x.com")

        with client.websocket_connect("/ws/voice") as ws1:
            snapshot = _auth_voice_ws(ws1, d1["access_token"])
            assert snapshot["users"] == []
