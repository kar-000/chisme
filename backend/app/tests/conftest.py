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

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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
