import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import AppError
from app.models.organization import OrgRole
from app.models.user import User
from app.services import org_service

router = APIRouter(prefix="/orgs", tags=["organizations"])


class CreateOrgRequest(BaseModel):
    name: str


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class UpdateRoleRequest(BaseModel):
    role: str


@router.post("", status_code=201)
async def create_org(
    body: CreateOrgRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org = await org_service.create_organization(db, user, body.name)
    await db.commit()
    return {"id": str(org.id), "name": org.name, "slug": org.slug, "plan": org.plan}


@router.get("")
async def list_orgs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await org_service.get_user_orgs(db, user.id)


@router.get("/{org_id}/members")
async def list_members(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await org_service.require_org_role(db, user.id, org_id, OrgRole.viewer)
    return await org_service.get_org_members(db, org_id)


@router.post("/{org_id}/invites", status_code=201)
async def invite_member(
    org_id: uuid.UUID,
    body: InviteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await org_service.require_org_role(db, user.id, org_id, OrgRole.admin)
    role = OrgRole(body.role) if body.role in [r.value for r in OrgRole] else OrgRole.member
    invite = await org_service.create_invite(db, org_id, body.email, role, user.id)
    await db.commit()
    return {"invite_id": str(invite.id), "token": invite.token, "email": invite.email, "expires_at": invite.expires_at.isoformat()}


@router.post("/invites/{token}/accept")
async def accept_invite(
    token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    membership = await org_service.accept_invite(db, token, user)
    await db.commit()
    return {"org_id": str(membership.org_id), "role": membership.role.value}


@router.put("/{org_id}/members/{member_user_id}/role")
async def update_role(
    org_id: uuid.UUID,
    member_user_id: uuid.UUID,
    body: UpdateRoleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await org_service.require_org_role(db, user.id, org_id, OrgRole.admin)
    role = OrgRole(body.role) if body.role in [r.value for r in OrgRole] else OrgRole.member
    ok = await org_service.update_member_role(db, org_id, member_user_id, role)
    if not ok:
        raise AppError("NOT_FOUND", "Member not found", 404)
    await db.commit()
    return {"status": "updated"}


@router.delete("/{org_id}/members/{member_user_id}", status_code=204)
async def remove_member(
    org_id: uuid.UUID,
    member_user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await org_service.require_org_role(db, user.id, org_id, OrgRole.admin)
    ok = await org_service.remove_member(db, org_id, member_user_id)
    if not ok:
        raise AppError("NOT_FOUND", "Member not found", 404)
    await db.commit()
