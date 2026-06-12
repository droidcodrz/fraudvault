from fastapi import APIRouter

from app.api.v1 import admin, auth, detect, keys, organizations, password, plans, profile, results, usage, webhooks

router = APIRouter(prefix="/v1")
router.include_router(auth.router)
router.include_router(password.router)
router.include_router(detect.router)
router.include_router(results.router)
router.include_router(keys.router)
router.include_router(usage.router)
router.include_router(webhooks.router)
router.include_router(organizations.router)
router.include_router(plans.router)
router.include_router(profile.router)
router.include_router(admin.router)
