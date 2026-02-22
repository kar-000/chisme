"""
WebSocket voice signaling tests.

Covers:
  - voice.join broadcasts voice.user_joined to channel
  - voice.leave broadcasts voice.user_left
  - voice.offer / voice.answer / voice.ice_candidate relayed to target user
  - Auto-leave on disconnect broadcasts voice.user_left
  - Signaling to non-voice target is silently dropped
  - Signaling with non-integer target_id is silently dropped
  - voice.state_snapshot sent to newly connected user when voice is occupied
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


def _make_channel(client: TestClient, headers: dict, name: str = "voice-room") -> int:
    resp = client.post("/api/channels", json={"name": name}, headers=headers)
    assert resp.status_code == 200
    return resp.json()["id"]


def _auth_ws(ws, token: str) -> None:
    """Send auth message and drain user.joined + presence.changed."""
    ws.send_json({"type": "auth", "token": token})
    ws.receive_json()  # user.joined (self)
    ws.receive_json()  # presence.changed (self online)


def _drain_join_events(ws) -> None:
    """Drain user.joined + presence.changed events sent when another user connects."""
    ws.receive_json()  # user.joined
    ws.receive_json()  # presence.changed


# ---------------------------------------------------------------------------
# Voice join / leave
# ---------------------------------------------------------------------------


class TestVoiceJoinLeave:
    def test_voice_join_broadcasts_user_joined(self, client: TestClient):
        """voice.join from user1 → voice.user_joined broadcast received by user2."""
        d1 = _register(client, "vj1a", "vj1a@x.com")
        d2 = _register(client, "vj1b", "vj1b@x.com")
        ch = _make_channel(client, {"Authorization": f"Bearer {d1['access_token']}"}, "vj-ch1")

        with client.websocket_connect(f"/ws/channels/{ch}") as ws1:
            _auth_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/channels/{ch}") as ws2:
                _auth_ws(ws2, d2["access_token"])
                _drain_join_events(ws1)  # ws1 sees ws2 join

                ws1.send_json({"type": "voice.join", "muted": False, "video": False})

                # ws2 should receive voice.user_joined
                event = ws2.receive_json()
                assert event["type"] == "voice.user_joined"
                assert event["user_id"] == d1["user"]["id"]
                assert event["muted"] is False

    def test_voice_leave_broadcasts_user_left(self, client: TestClient):
        """voice.leave from user1 → voice.user_left broadcast received by user2."""
        d1 = _register(client, "vl1a", "vl1a@x.com")
        d2 = _register(client, "vl1b", "vl1b@x.com")
        ch = _make_channel(client, {"Authorization": f"Bearer {d1['access_token']}"}, "vl-ch1")

        with client.websocket_connect(f"/ws/channels/{ch}") as ws1:
            _auth_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/channels/{ch}") as ws2:
                _auth_ws(ws2, d2["access_token"])
                _drain_join_events(ws1)

                ws1.send_json({"type": "voice.join", "muted": True, "video": False})
                ws2.receive_json()  # voice.user_joined

                ws1.send_json({"type": "voice.leave"})

                event = ws2.receive_json()
                assert event["type"] == "voice.user_left"
                assert event["user_id"] == d1["user"]["id"]

    def test_voice_disconnect_auto_leave(self, client: TestClient):
        """Closing WS while in voice → voice.user_left broadcast to remaining users."""
        d1 = _register(client, "vd1a", "vd1a@x.com")
        d2 = _register(client, "vd1b", "vd1b@x.com")
        ch = _make_channel(client, {"Authorization": f"Bearer {d1['access_token']}"}, "vd-ch1")

        with client.websocket_connect(f"/ws/channels/{ch}") as ws2:
            _auth_ws(ws2, d2["access_token"])

            with client.websocket_connect(f"/ws/channels/{ch}") as ws1:
                _auth_ws(ws1, d1["access_token"])
                _drain_join_events(ws2)  # ws2 sees ws1 join

                ws1.send_json({"type": "voice.join", "muted": False, "video": False})
                ws2.receive_json()  # voice.user_joined

            # ws1 context exits — connection closed
            # ws2 should see voice.user_left, then user.left, then presence.changed
            events = {ws2.receive_json()["type"] for _ in range(3)}
            assert "voice.user_left" in events


# ---------------------------------------------------------------------------
# Voice signaling relay
# ---------------------------------------------------------------------------


class TestVoiceSignalingRelay:
    def _setup_two_users_in_voice(self, client: TestClient, ch_name: str):
        """Register two users, connect both to a channel, both join voice.
        Returns (ws1, ws2, user1_id, user2_id) — callers must use as context mgrs."""
        d1 = _register(client, f"{ch_name}u1", f"{ch_name}u1@x.com")
        d2 = _register(client, f"{ch_name}u2", f"{ch_name}u2@x.com")
        ch = _make_channel(client, {"Authorization": f"Bearer {d1['access_token']}"}, ch_name)
        return d1, d2, ch

    def test_voice_offer_relayed_to_target(self, client: TestClient):
        """voice.offer from user1 targeting user2 is delivered to user2."""
        d1, d2, ch = self._setup_two_users_in_voice(client, "offerch")

        with client.websocket_connect(f"/ws/channels/{ch}") as ws1:
            _auth_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/channels/{ch}") as ws2:
                _auth_ws(ws2, d2["access_token"])
                _drain_join_events(ws1)

                # Both join voice
                ws1.send_json({"type": "voice.join", "muted": False, "video": False})
                ws2.receive_json()  # ws2 sees ws1 voice.user_joined
                ws1.receive_json()  # ws1 sees own voice.user_joined broadcast

                ws2.send_json({"type": "voice.join", "muted": True, "video": False})
                ws1.receive_json()  # ws1 sees ws2 voice.user_joined
                ws2.receive_json()  # ws2 sees own voice.user_joined broadcast

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
        d1, d2, ch = self._setup_two_users_in_voice(client, "answerch")

        with client.websocket_connect(f"/ws/channels/{ch}") as ws1:
            _auth_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/channels/{ch}") as ws2:
                _auth_ws(ws2, d2["access_token"])
                _drain_join_events(ws1)

                ws1.send_json({"type": "voice.join", "muted": False, "video": False})
                ws2.receive_json()
                ws1.receive_json()

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
        d1, d2, ch = self._setup_two_users_in_voice(client, "icech")

        with client.websocket_connect(f"/ws/channels/{ch}") as ws1:
            _auth_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/channels/{ch}") as ws2:
                _auth_ws(ws2, d2["access_token"])
                _drain_join_events(ws1)

                ws1.send_json({"type": "voice.join", "muted": False, "video": False})
                ws2.receive_json()
                ws1.receive_json()

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
        """voice.offer with a target not in voice is silently dropped — no message delivered."""
        d1, d2, ch = self._setup_two_users_in_voice(client, "dropch")

        with client.websocket_connect(f"/ws/channels/{ch}") as ws1:
            _auth_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/channels/{ch}") as ws2:
                _auth_ws(ws2, d2["access_token"])
                _drain_join_events(ws1)

                # Only ws1 joins voice; ws2 does NOT join
                ws1.send_json({"type": "voice.join", "muted": False, "video": False})
                ws2.receive_json()  # voice.user_joined
                ws1.receive_json()  # own voice.user_joined broadcast

                # ws1 tries to signal ws2 who is not in voice
                ws1.send_json(
                    {
                        "type": "voice.offer",
                        "target_user_id": d2["user"]["id"],
                        "sdp": {"type": "offer", "sdp": "fake"},
                    }
                )

                # ws2 should receive nothing — send a typing event and use that as a
                # sentinel: if ws2 receives typing BEFORE any offer, the offer was dropped
                ws1.send_json({"type": "user.typing"})
                sentinel = ws2.receive_json()
                assert sentinel["type"] == "user.typing"

    def test_offer_with_string_target_id_is_dropped(self, client: TestClient):
        """voice.offer with a non-integer target_user_id is silently dropped."""
        d1, d2, ch = self._setup_two_users_in_voice(client, "stridch")

        with client.websocket_connect(f"/ws/channels/{ch}") as ws1:
            _auth_ws(ws1, d1["access_token"])

            with client.websocket_connect(f"/ws/channels/{ch}") as ws2:
                _auth_ws(ws2, d2["access_token"])
                _drain_join_events(ws1)

                ws1.send_json({"type": "voice.join", "muted": False, "video": False})
                ws2.receive_json()
                ws1.receive_json()

                ws2.send_json({"type": "voice.join", "muted": True, "video": False})
                ws1.receive_json()
                ws2.receive_json()

                # Send string target_id — should be dropped
                ws1.send_json(
                    {
                        "type": "voice.offer",
                        "target_user_id": str(d2["user"]["id"]),  # string, not int
                        "sdp": {"type": "offer", "sdp": "fake"},
                    }
                )

                # Sentinel: typing event should arrive next, not an offer
                ws1.send_json({"type": "user.typing"})
                sentinel = ws2.receive_json()
                assert sentinel["type"] == "user.typing"


# ---------------------------------------------------------------------------
# Voice state snapshot
# ---------------------------------------------------------------------------


class TestVoiceStateSnapshot:
    def test_snapshot_sent_to_new_connection_when_voice_occupied(self, client: TestClient):
        """New WS connection receives voice.state_snapshot if voice is occupied."""
        d1 = _register(client, "snap1a", "snap1a@x.com")
        d2 = _register(client, "snap1b", "snap1b@x.com")
        ch = _make_channel(client, {"Authorization": f"Bearer {d1['access_token']}"}, "snap-ch1")

        with client.websocket_connect(f"/ws/channels/{ch}") as ws1:
            _auth_ws(ws1, d1["access_token"])
            ws1.send_json({"type": "voice.join", "muted": True, "video": False})
            ws1.receive_json()  # own voice.user_joined broadcast

            with client.websocket_connect(f"/ws/channels/{ch}") as ws2:
                ws2.send_json({"type": "auth", "token": d2["access_token"]})
                # ws2 should receive: user.joined, presence.changed, voice.state_snapshot
                events = {}
                for _ in range(3):
                    ev = ws2.receive_json()
                    events[ev["type"]] = ev

                assert "voice.state_snapshot" in events
                snapshot = events["voice.state_snapshot"]
                user_ids = [u["user_id"] for u in snapshot["users"]]
                assert d1["user"]["id"] in user_ids

    def test_no_snapshot_when_voice_empty(self, client: TestClient):
        """New WS connection does NOT receive voice.state_snapshot when voice is empty."""
        d1 = _register(client, "snap2a", "snap2a@x.com")
        ch = _make_channel(client, {"Authorization": f"Bearer {d1['access_token']}"}, "snap-ch2")

        with client.websocket_connect(f"/ws/channels/{ch}") as ws1:
            ws1.send_json({"type": "auth", "token": d1["access_token"]})
            ev1 = ws1.receive_json()
            ev2 = ws1.receive_json()
            types = {ev1["type"], ev2["type"]}
            # Only user.joined and presence.changed — no snapshot
            assert types == {"user.joined", "presence.changed"}
