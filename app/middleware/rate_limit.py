from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import redis.asyncio as aioredis

from app.config import get_settings
from app.services.billing_service import PLAN_RATE_LIMITS
from app.models.user import UserPlan

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/v1/"):
            return await call_next(request)

        plan = UserPlan.free
        rate_key_id = request.client.host if request.client else "unknown"

        auth_context = getattr(request.state, "auth_context", None)
        if auth_context:
            plan = auth_context.user.plan
            if auth_context.api_key:
                rate_key_id = str(auth_context.api_key.id)

        per_min, per_day = PLAN_RATE_LIMITS.get(plan, (10, 100))
        if per_min is None:
            return await call_next(request)

        try:
            redis = aioredis.from_url(settings.redis_url, decode_responses=True)
            for window, limit, suffix in [(60, per_min, "min"), (86400, per_day, "day")]:
                key = f"ratelimit:{rate_key_id}:{suffix}"
                count = await redis.incr(key)
                if count == 1:
                    await redis.expire(key, window)
                if count > limit:
                    await redis.aclose()
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": {
                                "code": "RATE_LIMIT_EXCEEDED",
                                "message": "Rate limit exceeded",
                                "details": {"window": suffix, "limit": limit},
                            }
                        },
                    )
            await redis.aclose()
        except Exception:
            pass

        return await call_next(request)
