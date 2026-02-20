"""
Tests for the Redis presence system.

Redis is fully mocked — no real Redis instance required.
Covers:
  - presence module unit tests (set_online, set_offline, heartbeat,
    get_status, get_bulk_status) with a fake async Redis client
  - graceful degradation when Redis is unavailable (client returns None)
  - presence REST API endpoints (GET/POST) via TestClient
"""

import pytest

import app.redis.presence as presence_mod
from app.tests.conftest import auth_headers


# ---------------------------------------------------------------------------
# Fake async Redis helpers
# ---------------------------------------------------------------------------

class FakeRedis:
    """Minimal in-memory fake that mimics redis.asyncio.Redis."""

    def __init__(self):
        self._data: dict[str, str] = {}
        self._ttls: dict[str, int] = {}
        self.pipeline_calls: list = []

    async def setex(self, key: str, ttl: int, value: str):
        self._data[key] = value
        self._ttls[key] = ttl

    async def get(self, key: str):
        return self._data.get(key)

    async def delete(self, key: str):
        self._data.pop(key, None)
        self._ttls.pop(key, None)

    async def expire(self, key: str, ttl: int):
        if key in self._data:
            self._ttls[key] = ttl
            return 1
        return 0

    def pipeline(self):
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, redis: FakeRedis):
        self._redis = redis
        self._ops: list = []

    def get(self, key: str):
        self._ops.append(("get", key))
        return self  # allows chaining

    async def execute(self):
        return [self._redis._data.get(k) for _, k in self._ops]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_redis(monkeypatch):
    """Replace get_redis() with a FakeRedis for every test in this module."""
    fake = FakeRedis()
    monkeypatch.setattr(presence_mod, "get_redis", lambda: fake)
    return fake


@pytest.fixture()
def no_redis(monkeypatch):
    """Simulate Redis being unavailable."""
    monkeypatch.setattr(presence_mod, "get_redis", lambda: None)


# ---------------------------------------------------------------------------
# Unit tests — presence module
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_online_stores_status(patch_redis):
    await presence_mod.set_online(42)
    assert patch_redis._data["presence:42"] == "online"
    assert patch_redis._ttls["presence:42"] > 0


@pytest.mark.asyncio
async def test_set_online_custom_status(patch_redis):
    await presence_mod.set_online(7, "away")
    assert patch_redis._data["presence:7"] == "away"


@pytest.mark.asyncio
async def test_set_online_invalid_status_is_noop(patch_redis):
    await presence_mod.set_online(9, "invisible")
    assert "presence:9" not in patch_redis._data


@pytest.mark.asyncio
async def test_set_offline_removes_key(patch_redis):
    patch_redis._data["presence:1"] = "online"
    await presence_mod.set_offline(1)
    assert "presence:1" not in patch_redis._data


@pytest.mark.asyncio
async def test_heartbeat_refreshes_ttl(patch_redis):
    patch_redis._data["presence:5"] = "online"
    patch_redis._ttls["presence:5"] = 10
    await presence_mod.heartbeat(5)
    # TTL should be reset to the configured value (not 10)
    assert patch_redis._ttls["presence:5"] > 10


@pytest.mark.asyncio
async def test_get_status_returns_value(patch_redis):
    patch_redis._data["presence:3"] = "dnd"
    result = await presence_mod.get_status(3)
    assert result == "dnd"


@pytest.mark.asyncio
async def test_get_status_missing_key_returns_offline(patch_redis):
    result = await presence_mod.get_status(999)
    assert result == "offline"


@pytest.mark.asyncio
async def test_get_bulk_status(patch_redis):
    patch_redis._data["presence:1"] = "online"
    patch_redis._data["presence:2"] = "away"
    result = await presence_mod.get_bulk_status([1, 2, 3])
    assert result[1] == "online"
    assert result[2] == "away"
    assert result[3] == "offline"


@pytest.mark.asyncio
async def test_get_bulk_status_empty_list(patch_redis):
    result = await presence_mod.get_bulk_status([])
    assert result == {}


# ---------------------------------------------------------------------------
# Graceful degradation when Redis is None
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_online_no_redis_is_noop(no_redis):
    # Should not raise
    await presence_mod.set_online(1)


@pytest.mark.asyncio
async def test_set_offline_no_redis_is_noop(no_redis):
    await presence_mod.set_offline(1)


@pytest.mark.asyncio
async def test_heartbeat_no_redis_is_noop(no_redis):
    await presence_mod.heartbeat(1)


@pytest.mark.asyncio
async def test_get_status_no_redis_returns_offline(no_redis):
    result = await presence_mod.get_status(1)
    assert result == "offline"


@pytest.mark.asyncio
async def test_get_bulk_status_no_redis_all_offline(no_redis):
    result = await presence_mod.get_bulk_status([1, 2, 3])
    assert all(v == "offline" for v in result.values())


# ---------------------------------------------------------------------------
# REST API tests
# ---------------------------------------------------------------------------

def test_get_own_presence(client, patch_redis):
    headers = auth_headers(client)
    resp = client.get("/api/users/me/presence", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "user_id" in data
    assert data["status"] == "offline"  # nothing set yet in fake Redis


def test_set_status_online(client, patch_redis):
    headers = auth_headers(client)
    resp = client.post("/api/users/me/status", json={"status": "online"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "online"


def test_set_status_away(client, patch_redis):
    headers = auth_headers(client)
    resp = client.post("/api/users/me/status", json={"status": "away"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "away"


def test_set_status_invalid(client, patch_redis):
    headers = auth_headers(client)
    resp = client.post("/api/users/me/status", json={"status": "invisible"}, headers=headers)
    assert resp.status_code == 422


def test_get_user_presence(client, patch_redis):
    # Register two users; check presence of the second
    from app.tests.conftest import register_user
    headers1 = auth_headers(client, username="alice", email="alice@example.com")
    resp2 = register_user(client, username="bob", email="bob@example.com")
    bob_id = resp2.json()["user"]["id"]

    resp = client.get(f"/api/users/{bob_id}/presence", headers=headers1)
    assert resp.status_code == 200
    assert resp.json()["user_id"] == bob_id
    assert resp.json()["status"] == "offline"


def test_get_user_presence_not_found(client, patch_redis):
    headers = auth_headers(client)
    resp = client.get("/api/users/99999/presence", headers=headers)
    assert resp.status_code == 404


def test_bulk_presence(client, patch_redis):
    headers = auth_headers(client)
    resp = client.get("/api/presence/bulk?ids=1,2,3", headers=headers)
    assert resp.status_code == 200
    statuses = resp.json()["statuses"]
    assert all(v == "offline" for v in statuses.values())


def test_bulk_presence_bad_ids(client, patch_redis):
    headers = auth_headers(client)
    resp = client.get("/api/presence/bulk?ids=abc,2", headers=headers)
    assert resp.status_code == 400


def test_presence_requires_auth(client):
    resp = client.get("/api/users/me/presence")
    assert resp.status_code in (401, 403)
