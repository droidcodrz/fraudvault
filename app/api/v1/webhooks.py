from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from app.config import get_settings
from app.database import get_db
from app.models.api_key import APIKey
from app.models.user import User, UserPlan

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
settings = get_settings()

PLAN_MAP = {
    "free": UserPlan.free,
    "starter": UserPlan.starter,
    "growth": UserPlan.growth,
    "pro": UserPlan.pro,
    "enterprise": UserPlan.enterprise,
}


@router.post("/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events for subscription and billing."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if settings.stripe_webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
        except Exception:
            from app.exceptions import AppError

            raise AppError("INVALID_WEBHOOK", "Invalid Stripe webhook signature", 400)
    else:
        import json

        event = json.loads(payload)

    event_type = event.get("type") if isinstance(event, dict) else event.type
    data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object

    if event_type == "customer.subscription.updated":
        customer_id = data.get("customer")
        plan_name = data.get("items", {}).get("data", [{}])[0].get("price", {}).get("lookup_key", "free")
        plan = PLAN_MAP.get(plan_name, UserPlan.free)
        await db.execute(
            update(User).where(User.stripe_customer_id == customer_id).values(plan=plan)
        )

    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")
        await db.execute(
            update(User).where(User.stripe_customer_id == customer_id).values(plan=UserPlan.free)
        )

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_active = False
            await db.execute(
                update(APIKey).where(APIKey.user_id == user.id).values(is_active=False)
            )

    return {"received": True}
