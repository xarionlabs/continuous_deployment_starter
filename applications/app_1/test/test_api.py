import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, UTC

from api.main import app
from data.db.connections import Base, get_db
from data.db.models.User import User

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture(scope="function")
def test_user(db_session):
    user = User(email="test@example.com", created_at=datetime.now(UTC))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def test_create_user(client):
    response = client.post(
        "/api/v1/users/",
        json={"email": "new@example.com"},
        headers={"X-API-Key": "test_api_key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "new@example.com"
    assert "id" in data
    assert "created_at" in data

def test_read_users(client, test_user):
    response = client.get(
        "/api/v1/users/",
        headers={"X-API-Key": "test_api_key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["email"] == "test@example.com"

def test_read_user(client, test_user):
    response = client.get(
        f"/api/v1/users/{test_user.id}",
        headers={"X-API-Key": "test_api_key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"

def test_read_user_not_found(client):
    response = client.get(
        "/api/v1/users/999",
        headers={"X-API-Key": "test_api_key"}
    )
    assert response.status_code == 404

def test_update_user(client, test_user):
    response = client.put(
        f"/api/v1/users/{test_user.id}",
        json={"email": "updated@example.com"},
        headers={"X-API-Key": "test_api_key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "updated@example.com"

def test_update_user_not_found(client):
    response = client.put(
        "/api/v1/users/999",
        json={"email": "updated@example.com"},
        headers={"X-API-Key": "test_api_key"}
    )
    assert response.status_code == 404

def test_delete_user(client, test_user):
    response = client.delete(
        f"/api/v1/users/{test_user.id}",
        headers={"X-API-Key": "test_api_key"}
    )
    assert response.status_code == 200
    
    # Verify user is deleted
    response = client.get(
        f"/api/v1/users/{test_user.id}",
        headers={"X-API-Key": "test_api_key"}
    )
    assert response.status_code == 404

def test_delete_user_not_found(client):
    response = client.delete(
        "/api/v1/users/999",
        headers={"X-API-Key": "test_api_key"}
    )
    assert response.status_code == 404

def test_missing_api_key(client):
    response = client.post(
        "/api/v1/users/",
        json={"email": "new@example.com"}
    )
    assert response.status_code == 403