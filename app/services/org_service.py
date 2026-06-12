import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import AppError
from app.models.organization import InviteStatus, OrgInvite, OrgMembership, OrgRole, Organization
from app.models.user import User


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:80] + "-" + secrets.token_hex(3)


async def create_organization(db: AsyncSession, user: User, name: str) -> Organization:
    org = Organization(name=name, slug=_slugify(name))
    db.add(org)
    await db.flush()

    membership = OrgMembership(org_id=org.id, user_id=user.id, role=OrgRole.owner)
    db.add(membership)

    user.current_org_id = org.id
    await db.flush()
    return org


async def get_user_orgs(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(OrgMembership)
        .options(selectinload(OrgMembership.organization))
        .where(OrgMembership.user_id == user_id)
    )
    memberships = result.scalars().all()
    return [
        {
            "id": str(m.organization.id),
            "name": m.organization.name,
            "slug": m.organization.slug,
            "plan": m.organization.plan,
            "role": m.role.value,
            "member_count": 0,
        }
        for m in memberships
    ]


async def get_org_members(db: AsyncSession, org_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(OrgMembership)
        .options(selectinload(OrgMembership.user))
        .where(OrgMembership.org_id == org_id)
    )
    return [
        {
            "id": str(m.id),
            "user_id": str(m.user.id),
            "email": m.user.email,
            "full_name": m.user.full_name,
            "role": m.role.value,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        }
        for m in result.scalars().all()
    ]


async def get_user_role_in_org(db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID) -> OrgRole | None:
    result = await db.execute(
        select(OrgMembership.role)
        .where(OrgMembership.user_id == user_id, OrgMembership.org_id == org_id)
    )
    row = result.scalar_one_or_none()
    return row


async def require_org_role(db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID, min_role: OrgRole) -> OrgRole:
    role = await get_user_role_in_org(db, user_id, org_id)
    if not role:
        raise AppError("FORBIDDEN", "Not a member of this organization", 403)
    hierarchy = {OrgRole.owner: 0, OrgRole.admin: 1, OrgRole.member: 2, OrgRole.viewer: 3}
    if hierarchy.get(role, 99) > hierarchy.get(min_role, 99):
        raise AppError("FORBIDDEN", f"Requires {min_role.value} role or higher", 403)
    return role


async def create_invite(
    db: AsyncSession, org_id: uuid.UUID, email: str, role: OrgRole, invited_by: uuid.UUID
) -> OrgInvite:
    existing = await db.execute(
        select(OrgMembership)
        .join(User)
        .where(OrgMembership.org_id == org_id, User.email == email)
    )
    if existing.scalar_one_or_none():
        raise AppError("ALREADY_MEMBER", "User is already a member", 409)

    token = secrets.token_urlsafe(48)
    invite = OrgInvite(
        org_id=org_id,
        email=email,
        role=role,
        token=token,
        invited_by=invited_by,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invite)
    await db.flush()
    return invite


async def accept_invite(db: AsyncSession, token: str, user: User) -> OrgMembership:
    result = await db.execute(
        select(OrgInvite).where(OrgInvite.token == token, OrgInvite.status == InviteStatus.pending)
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise AppError("INVALID_INVITE", "Invite not found or already used", 404)
    expires = invite.expires_at.replace(tzinfo=timezone.utc) if invite.expires_at.tzinfo is None else invite.expires_at
    if expires < datetime.now(timezone.utc):
        invite.status = InviteStatus.expired
        raise AppError("INVITE_EXPIRED", "This invite has expired", 410)
    if invite.email.lower() != user.email.lower():
        raise AppError("EMAIL_MISMATCH", "This invite was sent to a different email", 403)

    membership = OrgMembership(org_id=invite.org_id, user_id=user.id, role=invite.role)
    db.add(membership)
    invite.status = InviteStatus.accepted
    user.current_org_id = invite.org_id
    await db.flush()
    return membership


async def remove_member(db: AsyncSession, org_id: uuid.UUID, member_user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(OrgMembership)
        .where(OrgMembership.org_id == org_id, OrgMembership.user_id == member_user_id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        return False
    if membership.role == OrgRole.owner:
        raise AppError("CANNOT_REMOVE_OWNER", "Cannot remove the organization owner", 403)
    await db.delete(membership)
    await db.flush()
    return True


async def update_member_role(
    db: AsyncSession, org_id: uuid.UUID, member_user_id: uuid.UUID, new_role: OrgRole
) -> bool:
    result = await db.execute(
        select(OrgMembership)
        .where(OrgMembership.org_id == org_id, OrgMembership.user_id == member_user_id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        return False
    if membership.role == OrgRole.owner and new_role != OrgRole.owner:
        raise AppError("CANNOT_DEMOTE_OWNER", "Cannot change owner role", 403)
    membership.role = new_role
    await db.flush()
    return True
