"""
Pytest fixtures shared across all test modules.
Uses an in-memory SQLite database with StaticPool so all connections
share a single in-memory DB — no real Postgres required for tests.
"""

import os

# Set env vars BEFORE any app module is imported
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-min-32-chars-long!!"
os.environ["ALGORITHM"] = "HS256"
os.environ.setdefault("TENOR_API_KEY", "test-gif-api-key")  # prevent early-return in gif tests

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import event as sa_event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import app modules AFTER env vars are set
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# Single shared in-memory SQLite engine — StaticPool ensures all
# connections share the same DB instance.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# Enable FK enforcement so cascade-delete behaviour mirrors production PostgreSQL.
# SQLite has FK support but disables it by default.
@sa_event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def register_user(client: TestClient, username="testuser", email="test@example.com", password="Password1!"):
    return client.post("/api/auth/register", json={"username": username, "email": email, "password": password})


def auth_headers(client: TestClient, username="testuser", email="test@example.com", password="Password1!"):
    resp = register_user(client, username=username, email=email, password=password)
    assert resp.status_code == 200, f"Registration failed: {resp.json()}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def get_server_id(client: TestClient, headers: dict) -> int:
    """Return the ID of the first (main) server the authenticated user belongs to."""
    resp = client.get("/api/servers", headers=headers)
    assert resp.status_code == 200, f"Failed to get servers: {resp.json()}"
    servers = resp.json()
    assert len(servers) > 0, "User belongs to no servers"
    return servers[0]["id"]
