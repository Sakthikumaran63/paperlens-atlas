import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_registration(client: AsyncClient):
    payload = {
        "email": "researcher@example.com",
        "password": "SecurePassword123!",
        "name": "Dr. Researcher"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "researcher@example.com"
    assert data["user"]["name"] == "Dr. Researcher"
    assert "password" not in data["user"]
    assert "hashed_password" not in data["user"]


@pytest.mark.asyncio
async def test_duplicate_registration(client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "name": "User 1"
    }
    resp1 = await client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 400
    assert resp2.json()["detail"] == "A user with this email address already exists."


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # Register
    reg_payload = {
        "email": "login_user@example.com",
        "password": "CorrectPassword123!",
        "name": "Login User"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # Login
    login_payload = {
        "email": "login_user@example.com",
        "password": "CorrectPassword123!"
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login_user@example.com"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    reg_payload = {
        "email": "wrong_pwd@example.com",
        "password": "RightPassword123!"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "wrong_pwd@example.com",
        "password": "WrongPassword123!"
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient):
    reg_payload = {
        "email": "me@example.com",
        "password": "Password123!",
        "name": "Me User"
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["name"] == "Me User"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
