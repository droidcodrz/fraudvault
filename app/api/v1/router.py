from fastapi import APIRouter

from app.api.v1 import auth, detect, keys, results, usage, webhooks

router = APIRouter(prefix="/v1")
router.include_router(auth.router)
router.include_router(detect.router)
router.include_router(results.router)
router.include_router(keys.router)
router.include_router(usage.router)
router.include_router(webhooks.router)
