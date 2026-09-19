import pytest
from fastapi.testclient import TestClient


def test_register_user_success(client: TestClient):
    response = client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "password": "Password123!"}
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == "newuser@example.com"


def test_register_duplicate_email(client: TestClient):
    payload = {"email": "duplicate@example.com", "password": "Password123!"}
    res1 = client.post("/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()


def test_register_invalid_email(client: TestClient):
    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "Password123!"}
    )
    assert response.status_code == 422


def test_login_success(client: TestClient):
    email = "logintest@example.com"
    pwd = "ValidPassword123!"
    client.post("/auth/register", json={"email": email, "password": pwd})

    response = client.post("/auth/login", json={"email": email, "password": pwd})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_invalid_password(client: TestClient):
    email = "wrongpass@example.com"
    client.post("/auth/register", json={"email": email, "password": "CorrectPassword123!"})

    response = client.post("/auth/login", json={"email": email, "password": "WrongPassword"})
    assert response.status_code == 401


def test_login_nonexistent_user(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"email": "nonexistent@example.com", "password": "Password123!"}
    )
    assert response.status_code == 401


def test_get_current_user_me(client: TestClient, auth_headers: dict):
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert data["email"].endswith("@example.com")


def test_get_me_unauthorized(client: TestClient):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_get_me_invalid_token(client: TestClient):
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.payload"})
    assert response.status_code == 401
