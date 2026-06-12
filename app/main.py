from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

from app.api.v1.router import router as v1_router
from app.config import get_settings
from app.exceptions import AppError, app_error_handler, http_exception_handler
from app.middleware.api_key_auth import APIKeyAuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "detection_thresholds",
        ai_generated=settings.ai_generated_threshold,
        ai_inconclusive=settings.ai_inconclusive_threshold,
        forensic_tampered=settings.forensic_tampered_threshold,
        forensic_inconclusive=settings.forensic_inconclusive_threshold,
    )

    yield
    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="FraudVault API",
        description="Document and image forgery detection platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(APIKeyAuthMiddleware)

    app.include_router(v1_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(str(frontend_dir / "index.html"))

    return app


app = create_app()
