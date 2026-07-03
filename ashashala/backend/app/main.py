"""AshaShala FastAPI application factory.

Phase 1: app wiring, Sentry init, global exception handler, and the
/api/v1/health endpoint that pings every external service.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.session import close_db
from app.routes.admin import router as admin_router
from app.routes.health import router as health_router
from app.routes.parent import router as parent_router
from app.routes.school_admin import router as school_admin_router
from app.routes.student import router as student_router
from app.routes.teacher import router as teacher_router
from app.services.audit_service import AuditMiddleware

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialise Sentry if a DSN is configured (never crash if absent)."""
    if not settings.SENTRY_DSN:
        logger.info("SENTRY_DSN not set — error monitoring disabled")
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=0.1,
        )
        logger.info("Sentry initialised")
    except Exception as e:  # noqa: BLE001 — observability must never block startup
        logger.warning("Sentry init failed (continuing without it): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup/shutdown lifecycle."""
    logger.info("Starting AshaShala API v%s (%s)", settings.APP_VERSION, settings.ENVIRONMENT)
    init_sentry()
    yield
    await close_db()
    logger.info("AshaShala API shut down cleanly")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AshaShala API",
        description="Agentic AI Tutoring Platform",
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditMiddleware)

    register_exception_handlers(app)

    # Register the tenant-isolation session event (import side effect).
    from app.db import tenant_filter  # noqa: F401

    # Mount routers.
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(school_admin_router)
    app.include_router(teacher_router)
    app.include_router(student_router)
    app.include_router(parent_router)

    @app.get("/", tags=["Root"])
    async def root() -> dict:
        return {
            "name": "AshaShala API",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "health": "/api/v1/health",
            "docs": "/docs",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )
