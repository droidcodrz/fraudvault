"""Seed the database with plans, admin user, and demo organization.

Usage:
    python -m scripts.seed          # run all seeders
    python -m scripts.seed --plans  # seed plans only
    python -m scripts.seed --reset  # drop and re-seed
"""

import argparse
import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, Base
from app.models.organization import OrgMembership, OrgRole, Organization
from app.models.plan import Plan
from app.models.user import User, UserPlan, UserRole
from app.services.auth_service import hash_password


PLANS = [
    {
        "name": "free",
        "display_name": "Free",
        "description": "Get started with basic fraud detection",
        "monthly_price_cents": 0,
        "annual_price_cents": 0,
        "monthly_detection_limit": 50,
        "rate_limit_per_minute": 10,
        "rate_limit_per_day": 100,
        "max_file_size_mb": 10,
        "max_members": 1,
        "max_api_keys": 2,
        "features": "ELA analysis,Clone detection,Metadata analysis,Basic heatmaps",
        "sort_order": 0,
    },
    {
        "name": "starter",
        "display_name": "Starter",
        "description": "For individuals and small projects",
        "monthly_price_cents": 2900,
        "annual_price_cents": 29000,
        "monthly_detection_limit": 1000,
        "rate_limit_per_minute": 60,
        "rate_limit_per_day": 1000,
        "max_file_size_mb": 20,
        "max_members": 3,
        "max_api_keys": 5,
        "features": "Everything in Free,Provenance detection,PDF analysis,Priority processing",
        "sort_order": 1,
    },
    {
        "name": "growth",
        "display_name": "Growth",
        "description": "For growing teams and businesses",
        "monthly_price_cents": 7900,
        "annual_price_cents": 79000,
        "monthly_detection_limit": 10000,
        "rate_limit_per_minute": 120,
        "rate_limit_per_day": 10000,
        "max_file_size_mb": 50,
        "max_members": 10,
        "max_api_keys": 15,
        "features": "Everything in Starter,Team management,Webhook notifications,API access",
        "sort_order": 2,
    },
    {
        "name": "pro",
        "display_name": "Pro",
        "description": "For organizations with high-volume needs",
        "monthly_price_cents": 19900,
        "annual_price_cents": 199000,
        "monthly_detection_limit": 50000,
        "rate_limit_per_minute": 300,
        "rate_limit_per_day": 50000,
        "max_file_size_mb": 100,
        "max_members": 25,
        "max_api_keys": 50,
        "features": "Everything in Growth,Dedicated support,Custom webhooks,SLA guarantee",
        "sort_order": 3,
    },
    {
        "name": "enterprise",
        "display_name": "Enterprise",
        "description": "Custom solutions for large organizations",
        "monthly_price_cents": 0,
        "annual_price_cents": 0,
        "monthly_detection_limit": None,
        "rate_limit_per_minute": None,
        "rate_limit_per_day": None,
        "max_file_size_mb": 200,
        "max_members": 100,
        "max_api_keys": 200,
        "features": "Everything in Pro,Unlimited detections,On-premise option,Custom integrations,Dedicated account manager",
        "sort_order": 4,
    },
]

ADMIN_USER = {
    "email": "admin@fraudvault.io",
    "password": "Admin123!@#",
    "full_name": "FraudVault Admin",
}

DEMO_ORG = {
    "name": "FraudVault Demo",
    "slug": "fraudvault-demo",
}


async def seed_plans(db: AsyncSession):
    print("Seeding plans...")
    for plan_data in PLANS:
        existing = await db.execute(select(Plan).where(Plan.name == plan_data["name"]))
        if existing.scalar_one_or_none():
            print(f"  Plan '{plan_data['name']}' already exists, skipping")
            continue
        plan = Plan(**plan_data)
        db.add(plan)
        print(f"  Created plan: {plan_data['display_name']} (${plan_data['monthly_price_cents']/100:.0f}/mo)")
    await db.flush()


async def seed_admin(db: AsyncSession) -> User:
    print("Seeding admin user...")
    existing = await db.execute(select(User).where(User.email == ADMIN_USER["email"]))
    user = existing.scalar_one_or_none()
    if user:
        print(f"  Admin user '{ADMIN_USER['email']}' already exists")
        return user

    user = User(
        email=ADMIN_USER["email"],
        password_hash=hash_password(ADMIN_USER["password"]),
        full_name=ADMIN_USER["full_name"],
        plan=UserPlan.enterprise,
        role=UserRole.admin,
        email_verified=True,
    )
    db.add(user)
    await db.flush()
    print(f"  Created admin: {ADMIN_USER['email']} / {ADMIN_USER['password']}")
    return user


async def seed_demo_org(db: AsyncSession, admin_user: User):
    print("Seeding demo organization...")
    existing = await db.execute(select(Organization).where(Organization.slug == DEMO_ORG["slug"]))
    if existing.scalar_one_or_none():
        print(f"  Demo org '{DEMO_ORG['slug']}' already exists, skipping")
        return

    org = Organization(name=DEMO_ORG["name"], slug=DEMO_ORG["slug"], plan="enterprise")
    db.add(org)
    await db.flush()

    membership = OrgMembership(org_id=org.id, user_id=admin_user.id, role=OrgRole.owner)
    db.add(membership)

    admin_user.current_org_id = org.id
    await db.flush()
    print(f"  Created org: {DEMO_ORG['name']}")


async def seed_demo_users(db: AsyncSession, org_id: uuid.UUID | None = None):
    print("Seeding demo users...")
    demo_users = [
        {"email": "user@example.com", "password": "Password123!", "full_name": "Jane Smith", "plan": UserPlan.starter},
        {"email": "viewer@example.com", "password": "Password123!", "full_name": "Bob Viewer", "plan": UserPlan.free},
    ]
    for u_data in demo_users:
        existing = await db.execute(select(User).where(User.email == u_data["email"]))
        if existing.scalar_one_or_none():
            print(f"  User '{u_data['email']}' already exists, skipping")
            continue
        user = User(
            email=u_data["email"],
            password_hash=hash_password(u_data["password"]),
            full_name=u_data["full_name"],
            plan=u_data["plan"],
            email_verified=True,
        )
        db.add(user)
        await db.flush()
        print(f"  Created user: {u_data['email']} / {u_data['password']}")

        if org_id:
            membership = OrgMembership(
                org_id=org_id,
                user_id=user.id,
                role=OrgRole.member,
            )
            db.add(membership)
            user.current_org_id = org_id
            await db.flush()


async def run_seed(plans_only: bool = False, reset: bool = False):
    async with async_session_factory() as db:
        if reset:
            print("Resetting seed data...")
            for table in ["org_memberships", "org_invites", "email_verifications", "password_resets"]:
                await db.execute(text(f"DELETE FROM {table}"))
            await db.execute(text("DELETE FROM plans"))
            await db.execute(text("DELETE FROM users WHERE role = 'admin'"))
            await db.execute(text("DELETE FROM organizations WHERE slug = 'fraudvault-demo'"))
            await db.flush()
            print("  Cleared existing seed data")

        await seed_plans(db)

        if not plans_only:
            admin_user = await seed_admin(db)
            await seed_demo_org(db, admin_user)

            org_result = await db.execute(select(Organization).where(Organization.slug == DEMO_ORG["slug"]))
            org = org_result.scalar_one_or_none()
            await seed_demo_users(db, org.id if org else None)

        await db.commit()
        print("\nSeeding complete!")

        if not plans_only:
            print(f"\n  Admin login:  {ADMIN_USER['email']} / {ADMIN_USER['password']}")
            print(f"  Demo login:   user@example.com / Password123!")


def main():
    parser = argparse.ArgumentParser(description="Seed the FraudVault database")
    parser.add_argument("--plans", action="store_true", help="Seed plans only")
    parser.add_argument("--reset", action="store_true", help="Clear and re-seed data")
    args = parser.parse_args()
    asyncio.run(run_seed(plans_only=args.plans, reset=args.reset))


if __name__ == "__main__":
    main()
