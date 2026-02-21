"""
Tests for the Redis voice state system and voice REST API.

Redis is fully mocked — no real Redis instance required.
Covers:
  - voice module unit tests (join_voice, leave_voice, update_state, heartbeat,
    get_channel_voice_users, get_user_voice_state, get_bulk_voice_states)
  - graceful degradation when Redis is unavailable
  - voice REST API endpoint (GET /api/channels/{id}/voice)
"""

import json
import pytest

import app.redis.voice as voice_mod
from app.tests.conftest import auth_headers


# ---------------------------------------------------------------------------
# Fake async Redis helpers
# ---------------------------------------------------------------------------

class FakeRedis:
    """Minimal in-memory fake that mimics redis.asyncio.Redis for voice tests."""

    def __init__(self):
        self._data: dict[str, str] = {}
        self._sets: dict[str, set] = {}
        self._ttls: dict[str, int] = {}

    async def setex(self, key: str, ttl: int, value: str):
        self._data[key] = value
        self._ttls[key] = ttl

    async def get(self, key: str):
        return self._data.get(key)

    async def delete(self, key: str):
        self._data.pop(key, None)
        self._ttls.pop(key, None)

    async def expire(self, key: str, ttl: int):
        if key in self._data or key in self._sets:
            self._ttls[key] = ttl
            return 1
        return 0

    async def sadd(self, key: str, *members):
        if key not in self._sets:
            self._sets[key] = set()
        self._sets[key].update(members)

    async def srem(self, key: str, *members):
        if key in self._sets:
            self._sets[key].discard(*members)

    async def smembers(self, key: str):
        return self._sets.get(key, set())

    def pipeline(self):
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, redis: FakeRedis):
        self._redis = redis
        self._ops: list = []

    def sadd(self, key: str, *members):
        self._ops.append(("sadd", key, members))
        return self

    def srem(self, key: str, *members):
        self._ops.append(("srem", key, members))
        return self

    def expire(self, key: str, ttl: int):
        self._ops.append(("expire", key, ttl))
        return self

    def setex(self, key: str, ttl: int, value: str):
        self._ops.append(("setex", key, ttl, value))
        return self

    def delete(self, key: str):
        self._ops.append(("delete", key))
        return self

    def get(self, key: str):
        self._ops.append(("get", key))
        return self

    async def execute(self):
        results = []
        for op in self._ops:
            if op[0] == "sadd":
                await self._redis.sadd(op[1], *op[2])
                results.append(len(op[2]))
            elif op[0] == "srem":
                await self._redis.srem(op[1], *op[2])
                results.append(None)
            elif op[0] == "expire":
                result = await self._redis.expire(op[1], op[2])
                results.append(result)
            elif op[0] == "setex":
                await self._redis.setex(op[1], op[2], op[3])
                results.append(None)
            elif op[0] == "delete":
                await self._redis.delete(op[1])
                results.append(None)
            elif op[0] == "get":
                result = await self._redis.get(op[1])
                results.append(result)
        return results


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_redis(monkeypatch):
    """Replace get_redis() with a FakeRedis for every test in this module."""
    fake = FakeRedis()
    monkeypatch.setattr(voice_mod, "get_redis", lambda: fake)
    return fake


@pytest.fixture()
def no_redis(monkeypatch):
    """Simulate Redis being unavailable."""
    monkeypatch.setattr(voice_mod, "get_redis", lambda: None)


# ---------------------------------------------------------------------------
# Unit tests — voice module
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_join_voice_adds_user_to_channel_set(patch_redis):
    await voice_mod.join_voice(channel_id=1, user_id=42)
    assert "42" in patch_redis._sets.get("voice:1:users", set())


@pytest.mark.asyncio
async def test_join_voice_stores_user_state(patch_redis):
    await voice_mod.join_voice(channel_id=1, user_id=42, muted=True, video=False)
    raw = patch_redis._data.get("voice:user:42")
    assert raw is not None
    state = json.loads(raw)
    assert state["muted"] is True
    assert state["video"] is False
    assert state["channel_id"] == 1


@pytest.mark.asyncio
async def test_leave_voice_removes_user_from_set(patch_redis):
    patch_redis._sets["voice:1:users"] = {"42"}
    patch_redis._data["voice:user:42"] = json.dumps({"channel_id": 1, "muted": False, "video": False})
    await voice_mod.leave_voice(channel_id=1, user_id=42)
    assert "42" not in patch_redis._sets.get("voice:1:users", set())
    assert "voice:user:42" not in patch_redis._data


@pytest.mark.asyncio
async def test_update_state_changes_mute(patch_redis):
    await voice_mod.update_state(user_id=5, channel_id=2, muted=True, video=True)
    raw = patch_redis._data.get("voice:user:5")
    assert raw is not None
    state = json.loads(raw)
    assert state["muted"] is True
    assert state["video"] is True


@pytest.mark.asyncio
async def test_heartbeat_refreshes_ttl(patch_redis):
    patch_redis._sets["voice:1:users"] = {"10"}
    patch_redis._data["voice:user:10"] = json.dumps({"channel_id": 1, "muted": False, "video": False})
    patch_redis._ttls["voice:user:10"] = 1
    await voice_mod.heartbeat(channel_id=1, user_id=10)
    # TTL should have been refreshed to REDIS_PRESENCE_TTL
    from app.config import settings
    assert patch_redis._ttls.get("voice:user:10") == settings.REDIS_PRESENCE_TTL


@pytest.mark.asyncio
async def test_get_channel_voice_users_returns_list(patch_redis):
    patch_redis._sets["voice:3:users"] = {"1", "2", "3"}
    users = await voice_mod.get_channel_voice_users(channel_id=3)
    assert sorted(users) == [1, 2, 3]


@pytest.mark.asyncio
async def test_get_channel_voice_users_empty(patch_redis):
    users = await voice_mod.get_channel_voice_users(channel_id=99)
    assert users == []


@pytest.mark.asyncio
async def test_get_user_voice_state_returns_dict(patch_redis):
    state_data = {"channel_id": 1, "muted": False, "video": False}
    patch_redis._data["voice:user:7"] = json.dumps(state_data)
    state = await voice_mod.get_user_voice_state(user_id=7)
    assert state == state_data


@pytest.mark.asyncio
async def test_get_user_voice_state_returns_none_when_absent(patch_redis):
    state = await voice_mod.get_user_voice_state(user_id=999)
    assert state is None


@pytest.mark.asyncio
async def test_get_bulk_voice_states_mixed(patch_redis):
    patch_redis._data["voice:user:1"] = json.dumps({"channel_id": 1, "muted": True, "video": False})
    result = await voice_mod.get_bulk_voice_states([1, 2])
    assert result[1]["muted"] is True
    assert result[2] is None


@pytest.mark.asyncio
async def test_get_bulk_voice_states_empty_input(patch_redis):
    result = await voice_mod.get_bulk_voice_states([])
    assert result == {}


# ---------------------------------------------------------------------------
# Degradation tests — Redis unavailable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_join_voice_no_redis_is_noop(no_redis):
    await voice_mod.join_voice(channel_id=1, user_id=42)  # should not raise


@pytest.mark.asyncio
async def test_leave_voice_no_redis_is_noop(no_redis):
    await voice_mod.leave_voice(channel_id=1, user_id=42)


@pytest.mark.asyncio
async def test_get_channel_voice_users_no_redis_returns_empty(no_redis):
    users = await voice_mod.get_channel_voice_users(channel_id=1)
    assert users == []


@pytest.mark.asyncio
async def test_get_user_voice_state_no_redis_returns_none(no_redis):
    state = await voice_mod.get_user_voice_state(user_id=1)
    assert state is None


@pytest.mark.asyncio
async def test_get_bulk_voice_states_no_redis_returns_none_values(no_redis):
    result = await voice_mod.get_bulk_voice_states([1, 2, 3])
    assert all(v is None for v in result.values())


# ---------------------------------------------------------------------------
# REST API tests — GET /api/channels/{id}/voice
# ---------------------------------------------------------------------------

def test_get_voice_channel_requires_auth(client):
    resp = client.get("/api/channels/1/voice")
    assert resp.status_code in (401, 403)


def test_get_voice_channel_not_found(client):
    headers = auth_headers(client, username="voiceuser1", email="voice1@example.com")
    resp = client.get("/api/channels/99999/voice", headers=headers)
    assert resp.status_code == 404


def test_get_voice_channel_empty(client, patch_redis):
    headers = auth_headers(client, username="voiceuser2", email="voice2@example.com")
    # Create a channel first
    ch_resp = client.post(
        "/api/channels/",
        json={"name": "voice-test", "description": ""},
        headers=headers,
    )
    assert ch_resp.status_code in (200, 201)
    channel_id = ch_resp.json()["id"]

    resp = client.get(f"/api/channels/{channel_id}/voice", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["channel_id"] == channel_id
    assert body["users"] == []


def test_get_voice_channel_with_users(client, patch_redis):
    headers = auth_headers(client, username="voiceuser3", email="voice3@example.com")
    ch_resp = client.post(
        "/api/channels/",
        json={"name": "voice-test-2", "description": ""},
        headers=headers,
    )
    assert ch_resp.status_code in (200, 201)
    channel_id = ch_resp.json()["id"]

    # Seed fake Redis directly
    patch_redis._sets[f"voice:{channel_id}:users"] = {"1"}
    patch_redis._data["voice:user:1"] = json.dumps(
        {"channel_id": channel_id, "muted": True, "video": False}
    )

    resp = client.get(f"/api/channels/{channel_id}/voice", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["channel_id"] == channel_id
    assert len(body["users"]) == 1
    assert body["users"][0]["muted"] is True
    assert body["users"][0]["video"] is False
