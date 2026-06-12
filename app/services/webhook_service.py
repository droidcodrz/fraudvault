import asyncio
import hashlib
import hmac
import json
import time

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()

RETRY_DELAYS = [1, 2, 4]
TIMEOUT_SECONDS = 10


def _sign_payload(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def deliver_webhook(webhook_url: str, payload: dict) -> None:
    settings = get_settings()
    body = json.dumps(payload, default=str).encode()
    signature = _sign_payload(body, settings.secret_key)
    headers = {
        "Content-Type": "application/json",
        "X-FraudVault-Signature": signature,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        for attempt, delay in enumerate(RETRY_DELAYS):
            try:
                resp = await client.post(webhook_url, content=body, headers=headers)
                resp.raise_for_status()
                logger.info(
                    "webhook_delivered",
                    url=webhook_url,
                    status_code=resp.status_code,
                    attempt=attempt + 1,
                )
                return
            except Exception as exc:
                logger.warning(
                    "webhook_attempt_failed",
                    url=webhook_url,
                    attempt=attempt + 1,
                    error=str(exc),
                )
                if attempt < len(RETRY_DELAYS) - 1:
                    await asyncio.sleep(delay)

    logger.error("webhook_delivery_failed", url=webhook_url, attempts=len(RETRY_DELAYS))


def deliver_webhook_sync(webhook_url: str, payload: dict) -> None:
    settings = get_settings()
    body = json.dumps(payload, default=str).encode()
    signature = _sign_payload(body, settings.secret_key)
    headers = {
        "Content-Type": "application/json",
        "X-FraudVault-Signature": signature,
    }

    for attempt, delay in enumerate(RETRY_DELAYS):
        try:
            resp = httpx.post(webhook_url, content=body, headers=headers, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            logger.info(
                "webhook_delivered",
                url=webhook_url,
                status_code=resp.status_code,
                attempt=attempt + 1,
            )
            return
        except Exception as exc:
            logger.warning(
                "webhook_attempt_failed",
                url=webhook_url,
                attempt=attempt + 1,
                error=str(exc),
            )
            if attempt < len(RETRY_DELAYS) - 1:
                time.sleep(delay)

    logger.error("webhook_delivery_failed", url=webhook_url, attempts=len(RETRY_DELAYS))
