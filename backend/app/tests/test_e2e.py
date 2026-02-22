"""End-to-end flow tests — full user journeys."""

from fastapi.testclient import TestClient

from app.tests.conftest import register_user


class TestFullChatFlow:
    def test_register_login_chat_react(self, client: TestClient):
        # 1. Register
        reg = register_user(client, username="alice", email="alice@example.com")
        assert reg.status_code == 200
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Verify identity
        me = client.get("/api/auth/me", headers=headers)
        assert me.json()["username"] == "alice"

        # 3. Create channel
        ch = client.post("/api/channels", json={"name": "e2e-chat", "description": "E2E test"}, headers=headers)
        assert ch.status_code == 200
        ch_id = ch.json()["id"]

        # 4. Send message
        msg = client.post(f"/api/channels/{ch_id}/messages", json={"content": "Hola!"}, headers=headers)
        assert msg.status_code == 200
        msg_id = msg.json()["id"]

        # 5. React to message
        react = client.post(f"/api/messages/{msg_id}/reactions", json={"emoji": "🎉"}, headers=headers)
        assert react.status_code == 200

        # 6. Read message history — reaction should be included
        history = client.get(f"/api/channels/{ch_id}/messages", headers=headers)
        assert history.status_code == 200
        messages = history.json()["messages"]
        assert any(any(r["emoji"] == "🎉" for r in m.get("reactions", [])) for m in messages)

        # 7. Edit message
        edit = client.put(f"/api/messages/{msg_id}", json={"content": "Hola editado!"}, headers=headers)
        assert edit.status_code == 200
        assert edit.json()["edited_at"] is not None

        # 8. Delete message
        delete = client.delete(f"/api/messages/{msg_id}", headers=headers)
        assert delete.status_code == 200

        # 9. Health check
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "healthy"
