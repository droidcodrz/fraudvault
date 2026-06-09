import uuid

import pytest


@pytest.mark.asyncio
async def test_register_login_and_protected_endpoint(client):
    email = f"auth_{uuid.uuid4().hex[:8]}@example.com"
    password = "securepass123"

    register_resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Auth Test"},
    )
    assert register_resp.status_code == 201
    reg_data = register_resp.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == email

    login_resp = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    usage_resp = await client.get(
        "/v1/usage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert usage_resp.status_code == 200
    assert "total_hits" in usage_resp.json()


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    resp = await client.post(
        "/v1/auth/login",
        json={"email": "nobody@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"
