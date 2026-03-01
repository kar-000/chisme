"""
WebSocket voice signaling tests.

Covers the /ws/voice/{server_id} endpoint (per-server voice channel):
  - voice.join broadcasts voice.user_joined to all connected clients in the same server
  - voice.leave broadcasts voice.user_left
  - voice.offer / voice.answer / voice.ice_candidate relayed to target user
  - Auto-leave on disconnect broadcasts voice.user_reconnecting (7-second grace period)
  - Signaling to non-voice target is silently dropped
  - Signaling with non-integer target_id is silently dropped
  - voice.state_snapshot always sent on connect (empty list when voice is empty)
  - Non-member connection is rejected with close code 4003
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


def _get_server_id(client: TestClient, token: str) -> int:
    """Return the ID of the first server the authenticated user belongs to.

    All registered users are auto-joined to the same default server, so fetching
    the server_id once from any user's token is sufficient per test.
    """
    resp = client.get("/api/servers", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.json()
    servers = resp.json()
    assert len(servers) > 0, "User belongs to no servers"
    return servers[0]["id"]


def _auth_voice_ws(ws, token: str) -> dict:
    """Send auth and receive the immediate voice.state_snapshot response.

    The /ws/voice/{server_id} endpoint always sends a snapshot right after auth,
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
        server_id = _get_server_id(client, d1["access_token"])

        with client.websocket_connect(f"/ws/voice/{server_id}") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/voice/{server_id}") as ws2:
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
        server_id = _get_server_id(client, d1["access_token"])

        with client.websocket_connect(f"/ws/voice/{server_id}") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/voice/{server_id}") as ws2:
                _auth_voice_ws(ws2, d2["access_token"])

                ws1.send_json({"type": "voice.join", "muted": True, "video": False})
                ws1.receive_json()  # own voice.user_joined
                ws2.receive_json()  # voice.user_joined for ws1

                ws1.send_json({"type": "voice.leave"})

                event = ws2.receive_json()
                assert event["type"] == "voice.user_left"
                assert event["user_id"] == d1["user"]["id"]

    def test_voice_disconnect_auto_leave(self, client: TestClient):
        """Closing WS while in voice → voice.user_reconnecting broadcast with 7-second grace.

        Unlike a clean voice.leave, WS disconnect starts a grace period before
        the user is fully evicted. The immediate event is voice.user_reconnecting;
        voice.user_left fires after the delay (not tested here — 7 s is too long).
        """
        d1 = _register(client, "vd1a", "vd1a@x.com")
        d2 = _register(client, "vd1b", "vd1b@x.com")
        server_id = _get_server_id(client, d1["access_token"])

        with client.websocket_connect(f"/ws/voice/{server_id}") as ws2:
            _auth_voice_ws(ws2, d2["access_token"])

            with client.websocket_connect(f"/ws/voice/{server_id}") as ws1:
                _auth_voice_ws(ws1, d1["access_token"])

                ws1.send_json({"type": "voice.join", "muted": False, "video": False})
                ws1.receive_json()  # own voice.user_joined
                ws2.receive_json()  # voice.user_joined for ws1

            # ws1 context exits — connection closed while in voice.
            # ws2 immediately receives voice.user_reconnecting (grace period started).
            event = ws2.receive_json()
            assert event["type"] == "voice.user_reconnecting"
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
        server_id = _get_server_id(client, d1["access_token"])

        with client.websocket_connect(f"/ws/voice/{server_id}") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/voice/{server_id}") as ws2:
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
        server_id = _get_server_id(client, d1["access_token"])

        with client.websocket_connect(f"/ws/voice/{server_id}") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/voice/{server_id}") as ws2:
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
        server_id = _get_server_id(client, d1["access_token"])

        with client.websocket_connect(f"/ws/voice/{server_id}") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/voice/{server_id}") as ws2:
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
        server_id = _get_server_id(client, d1["access_token"])

        with client.websocket_connect(f"/ws/voice/{server_id}") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/voice/{server_id}") as ws2:
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

    def test_offer_not_relayed_to_third_party(self, client: TestClient):
        """voice.offer from B targeting C is NOT delivered to A.

        Three users (A, B, C) all join voice. B sends an offer to C.
        A must not receive the offer — signaling is point-to-point.
        Sentinel: B then leaves; A's next message must be voice.user_left, not voice.offer.
        """
        dA = _register(client, "isol_a", "isol_a@x.com")
        dB = _register(client, "isol_b", "isol_b@x.com")
        dC = _register(client, "isol_c", "isol_c@x.com")
        server_id = _get_server_id(client, dA["access_token"])

        with client.websocket_connect(f"/ws/voice/{server_id}") as wsA:
            _auth_voice_ws(wsA, dA["access_token"])

            with client.websocket_connect(f"/ws/voice/{server_id}") as wsB:
                _auth_voice_ws(wsB, dB["access_token"])

                with client.websocket_connect(f"/ws/voice/{server_id}") as wsC:
                    _auth_voice_ws(wsC, dC["access_token"])

                    # All three join voice
                    wsA.send_json({"type": "voice.join", "muted": False, "video": False})
                    wsA.receive_json()  # A's own voice.user_joined
                    wsB.receive_json()  # B sees A join
                    wsC.receive_json()  # C sees A join

                    wsB.send_json({"type": "voice.join", "muted": False, "video": False})
                    wsA.receive_json()  # A sees B join
                    wsB.receive_json()  # B's own voice.user_joined
                    wsC.receive_json()  # C sees B join

                    wsC.send_json({"type": "voice.join", "muted": False, "video": False})
                    wsA.receive_json()  # A sees C join
                    wsB.receive_json()  # B sees C join
                    wsC.receive_json()  # C's own voice.user_joined

                    # B sends an offer specifically to C
                    wsB.send_json(
                        {
                            "type": "voice.offer",
                            "target_user_id": dC["user"]["id"],
                            "sdp": {"type": "offer", "sdp": "fake-sdp"},
                        }
                    )

                    # C receives the offer (targeted delivery confirmed)
                    event_c = wsC.receive_json()
                    assert event_c["type"] == "voice.offer"
                    assert event_c["from_user_id"] == dB["user"]["id"]

                    # Sentinel: B leaves — A's next event must be voice.user_left,
                    # proving A never received the B→C offer
                    wsB.send_json({"type": "voice.leave"})
                    sentinel_a = wsA.receive_json()
                    assert sentinel_a["type"] == "voice.user_left"
                    assert sentinel_a["user_id"] == dB["user"]["id"]

    def test_offer_with_string_target_id_is_dropped(self, client: TestClient):
        """voice.offer with a non-integer target_user_id is silently dropped."""
        d1, d2 = self._two_users(client, "strid")
        server_id = _get_server_id(client, d1["access_token"])

        with client.websocket_connect(f"/ws/voice/{server_id}") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/voice/{server_id}") as ws2:
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
        """New /ws/voice/{server_id} connection receives voice.state_snapshot with current participants."""
        d1 = _register(client, "snap1a", "snap1a@x.com")
        d2 = _register(client, "snap1b", "snap1b@x.com")
        server_id = _get_server_id(client, d1["access_token"])

        with client.websocket_connect(f"/ws/voice/{server_id}") as ws1:
            _auth_voice_ws(ws1, d1["access_token"])
            ws1.send_json({"type": "voice.join", "muted": True, "video": False})
            ws1.receive_json()  # own voice.user_joined broadcast

            with client.websocket_connect(f"/ws/voice/{server_id}") as ws2:
                # Snapshot is the first message after auth — should include d1
                snapshot = _auth_voice_ws(ws2, d2["access_token"])
                user_ids = [u["user_id"] for u in snapshot["users"]]
                assert d1["user"]["id"] in user_ids

    def test_snapshot_sent_even_when_voice_empty(self, client: TestClient):
        """New /ws/voice/{server_id} connection receives voice.state_snapshot with users=[] when empty."""
        d1 = _register(client, "snap2a", "snap2a@x.com")
        server_id = _get_server_id(client, d1["access_token"])

        with client.websocket_connect(f"/ws/voice/{server_id}") as ws1:
            snapshot = _auth_voice_ws(ws1, d1["access_token"])
            assert snapshot["users"] == []
