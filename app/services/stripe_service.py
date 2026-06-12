import json
import logging

import stripe
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import AppError
from app.models.organization import Organization
from app.models.plan import Plan

settings = get_settings()
stripe.api_key = settings.stripe_secret_key
logger = logging.getLogger(__name__)


async def create_checkout_session(
    org: Organization,
    plan: Plan,
    billing_period: str,
    success_url: str,
    cancel_url: str,
) -> stripe.checkout.Session:
    price_id = plan.stripe_monthly_price_id if billing_period == "monthly" else plan.stripe_annual_price_id
    if not price_id:
        raise AppError("NO_PRICE", f"No Stripe price configured for {plan.name} ({billing_period})", 400)

    params: dict = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"org_id": str(org.id), "plan_name": plan.name},
    }

    if org.stripe_customer_id:
        params["customer"] = org.stripe_customer_id
    else:
        params["customer_creation"] = "always"

    return stripe.checkout.Session.create(**params)


def create_customer_portal_session(org: Organization, return_url: str) -> stripe.billing_portal.Session:
    if not org.stripe_customer_id:
        raise AppError("NO_CUSTOMER", "Organization has no Stripe customer", 400)

    return stripe.billing_portal.Session.create(
        customer=org.stripe_customer_id,
        return_url=return_url,
    )


async def _resolve_plan_name_from_price(db: AsyncSession, price_id: str) -> str | None:
    result = await db.execute(
        select(Plan.name).where(
            (Plan.stripe_monthly_price_id == price_id) | (Plan.stripe_annual_price_id == price_id)
        )
    )
    return result.scalar_one_or_none()


async def handle_webhook_event(db: AsyncSession, payload: bytes, sig_header: str) -> dict:
    if settings.stripe_webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
        except Exception:
            raise AppError("INVALID_WEBHOOK", "Invalid Stripe webhook signature", 400)
    else:
        event = json.loads(payload)

    event_type = event.get("type") if isinstance(event, dict) else event.type
    data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, data)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(db, data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, data)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, data)

    return {"received": True}


async def _handle_checkout_completed(db: AsyncSession, data: dict) -> None:
    org_id = (data.get("metadata") or {}).get("org_id")
    plan_name = (data.get("metadata") or {}).get("plan_name")
    customer_id = data.get("customer")
    subscription_id = data.get("subscription")

    if not org_id:
        return

    values: dict = {}
    if customer_id:
        values["stripe_customer_id"] = customer_id
    if subscription_id:
        values["stripe_subscription_id"] = subscription_id
    if plan_name:
        values["plan"] = plan_name

    if values:
        await db.execute(update(Organization).where(Organization.id == org_id).values(**values))


async def _handle_subscription_updated(db: AsyncSession, data: dict) -> None:
    customer_id = data.get("customer")
    if not customer_id:
        return

    items = data.get("items", {})
    item_list = items.get("data", []) if isinstance(items, dict) else []
    if not item_list:
        return

    price_id = item_list[0].get("price", {}).get("id")
    if not price_id:
        return

    plan_name = await _resolve_plan_name_from_price(db, price_id)
    if not plan_name:
        return

    await db.execute(
        update(Organization).where(Organization.stripe_customer_id == customer_id).values(plan=plan_name)
    )


async def _handle_subscription_deleted(db: AsyncSession, data: dict) -> None:
    customer_id = data.get("customer")
    if not customer_id:
        return

    await db.execute(
        update(Organization)
        .where(Organization.stripe_customer_id == customer_id)
        .values(plan="free", stripe_subscription_id=None)
    )


async def _handle_payment_failed(db: AsyncSession, data: dict) -> None:
    customer_id = data.get("customer")
    if not customer_id:
        return

    logger.warning("Payment failed for Stripe customer %s", customer_id)
