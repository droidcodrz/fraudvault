"""Tests for SaaS features: orgs, plans, admin, password reset, email verification."""
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient


# ── Auth improvements ───────────────────────────────────────────

class TestPasswordReset:
    @pytest.mark.asyncio
    async def test_forgot_password_returns_token(self, client: AsyncClient, auth_headers):
        email = f"pwreset_{uuid.uuid4().hex[:8]}@example.com"
        await client.post("/v1/auth/register", json={"email": email, "password": "testpass123"})

        res = await client.post("/v1/auth/forgot-password", json={"email": email})
        assert res.status_code == 200
        assert "token" in res.json()

    @pytest.mark.asyncio
    async def test_reset_password_works(self, client: AsyncClient):
        email = f"reset_{uuid.uuid4().hex[:8]}@example.com"
        await client.post("/v1/auth/register", json={"email": email, "password": "oldpass123"})

        forgot = await client.post("/v1/auth/forgot-password", json={"email": email})
        token = forgot.json()["token"]

        res = await client.post("/v1/auth/reset-password", json={"token": token, "password": "newpass12345"})
        assert res.status_code == 200

        login = await client.post("/v1/auth/login", json={"email": email, "password": "newpass12345"})
        assert login.status_code == 200

    @pytest.mark.asyncio
    async def test_forgot_nonexistent_email_still_200(self, client: AsyncClient):
        res = await client.post("/v1/auth/forgot-password", json={"email": "nobody@test.com"})
        assert res.status_code == 200


class TestEmailVerification:
    @pytest.mark.asyncio
    async def test_send_and_verify(self, client: AsyncClient, auth_headers):
        res = await client.post("/v1/auth/send-verification", headers=auth_headers)
        assert res.status_code == 200
        token = res.json()["token"]

        verify = await client.post("/v1/auth/verify-email", json={"token": token})
        assert verify.status_code == 200


# ── Organizations ───────────────────────────────────────────────

class TestOrganizations:
    @pytest.mark.asyncio
    async def test_create_and_list_org(self, client: AsyncClient, auth_headers):
        res = await client.post("/v1/orgs", json={"name": "Test Corp"}, headers=auth_headers)
        assert res.status_code == 201
        org_id = res.json()["id"]

        orgs = await client.get("/v1/orgs", headers=auth_headers)
        assert orgs.status_code == 200
        assert any(o["id"] == org_id for o in orgs.json())

    @pytest.mark.asyncio
    async def test_list_members(self, client: AsyncClient, auth_headers):
        res = await client.post("/v1/orgs", json={"name": "Members Corp"}, headers=auth_headers)
        org_id = res.json()["id"]

        members = await client.get(f"/v1/orgs/{org_id}/members", headers=auth_headers)
        assert members.status_code == 200
        assert len(members.json()) == 1
        assert members.json()[0]["role"] == "owner"

    @pytest.mark.asyncio
    async def test_invite_and_accept(self, client: AsyncClient, auth_headers):
        new_email = f"invited_{uuid.uuid4().hex[:8]}@example.com"

        org_res = await client.post("/v1/orgs", json={"name": "Invite Corp"}, headers=auth_headers)
        org_id = org_res.json()["id"]

        invite = await client.post(
            f"/v1/orgs/{org_id}/invites",
            json={"email": new_email, "role": "member"},
            headers=auth_headers,
        )
        assert invite.status_code == 201
        token = invite.json()["token"]

        reg = await client.post("/v1/auth/register", json={
            "email": new_email, "password": "member12345"
        })
        member_headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

        accept = await client.post(f"/v1/orgs/invites/{token}/accept", headers=member_headers)
        assert accept.status_code == 200

        members = await client.get(f"/v1/orgs/{org_id}/members", headers=member_headers)
        assert len(members.json()) == 2


# ── Plans ───────────────────────────────────────────────────────

class TestPlans:
    @pytest.mark.asyncio
    async def test_list_plans_public(self, client: AsyncClient):
        res = await client.get("/v1/plans")
        assert res.status_code == 200
        assert isinstance(res.json(), list)


# ── Admin ───────────────────────────────────────────────────────

class TestAdmin:
    @pytest.mark.asyncio
    async def test_admin_stats(self, client: AsyncClient, db_session):
        email = f"adm_{uuid.uuid4().hex[:8]}@example.com"
        reg = await client.post("/v1/auth/register", json={"email": email, "password": "admin12345"})
        token = reg.json()["access_token"]

        from app.models.user import User, UserRole
        from sqlalchemy import update
        await db_session.execute(update(User).where(User.email == email).values(role=UserRole.admin))
        await db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        res = await client.get("/v1/admin/stats", headers=headers)
        assert res.status_code == 200
        assert "total_users" in res.json()

    @pytest.mark.asyncio
    async def test_non_admin_rejected(self, client: AsyncClient, auth_headers):
        res = await client.get("/v1/admin/stats", headers=auth_headers)
        assert res.status_code == 403


# ── User response includes new fields ──────────────────────────

class TestUserResponse:
    @pytest.mark.asyncio
    async def test_register_returns_role_and_verified(self, client: AsyncClient):
        res = await client.post("/v1/auth/register", json={
            "email": f"new_{uuid.uuid4().hex[:8]}@test.com", "password": "newuser12345"
        })
        assert res.status_code == 201
        user = res.json()["user"]
        assert user["role"] == "user"
        assert user["email_verified"] is False
