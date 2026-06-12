from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import AppError
from app.models.organization import OrgRole, Organization
from app.models.plan import Plan
from app.models.user import User
from app.services import org_service
from app.services import stripe_service

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan_name: str
    billing_period: str = "monthly"
    success_url: str
    cancel_url: str


class PortalRequest(BaseModel):
    return_url: str


async def _get_user_org(db: AsyncSession, user: User) -> Organization:
    if not user.current_org_id:
        raise AppError("NO_ORG", "User has no active organization", 400)
    result = await db.execute(select(Organization).where(Organization.id == user.current_org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise AppError("NOT_FOUND", "Organization not found", 404)
    return org


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout session for subscribing to a plan."""
    org = await _get_user_org(db, user)
    await org_service.require_org_role(db, user.id, org.id, OrgRole.admin)

    if body.billing_period not in ("monthly", "annual"):
        raise AppError("INVALID_PERIOD", "billing_period must be 'monthly' or 'annual'", 400)

    result = await db.execute(select(Plan).where(Plan.name == body.plan_name, Plan.is_active == True))
    plan = result.scalar_one_or_none()
    if not plan:
        raise AppError("PLAN_NOT_FOUND", f"Plan '{body.plan_name}' not found", 404)

    session = await stripe_service.create_checkout_session(
        org=org,
        plan=plan,
        billing_period=body.billing_period,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
    )
    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/portal")
async def create_portal(
    body: PortalRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Customer Portal session for managing the subscription."""
    org = await _get_user_org(db, user)
    await org_service.require_org_role(db, user.id, org.id, OrgRole.admin)

    session = stripe_service.create_customer_portal_session(org=org, return_url=body.return_url)
    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events for organization billing."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    return await stripe_service.handle_webhook_event(db, payload, sig_header)
