import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure PBNC root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.core.database as app_db
from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings

TEST_DB_FILE = "./test_suite.db"

# Shared SQLite engine for consistent database across API and background pipeline
test_engine = create_engine(
    f"sqlite:///{TEST_DB_FILE}",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Point global SessionLocal to the shared test database
app_db.engine = test_engine
app_db.SessionLocal = TestingSessionLocal


@pytest.fixture(scope="session", autouse=True)
def setup_test_suite():
    """Create test upload directory and clean up test database after all tests."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass
    Base.metadata.create_all(bind=test_engine)
    yield
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


@pytest.fixture(scope="function")
def db_session():
    """Provide a fresh transactional session for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden database dependency."""
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(client):
    """Register and login a unique user for each test, returning Bearer auth headers."""
    import uuid
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecretPassword123!"

    # Register
    client.post("/auth/register", json={"email": email, "password": password})

    # Login
    resp = client.post("/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def second_user_headers(client):
    """Register and login a secondary user for multi-tenancy authorization tests."""
    import uuid
    email = f"second_{uuid.uuid4().hex[:8]}@example.com"
    password = "AnotherPassword123!"

    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
