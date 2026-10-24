"""FastAPI app. Domain routers are mounted only when their milestone is built (docs/07)."""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import install_error_handlers
from app.routers import (
    auth,
    billing,
    charges,
    complaints,
    compliance,
    dev,
    flats,
    home,
    imports,
    internal_jobs,
    payments,
    societies,
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SocietyIQ API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)

    api = APIRouter(prefix="/api/v1")

    @api.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    api.include_router(auth.router)
    api.include_router(societies.router)
    api.include_router(flats.router)
    api.include_router(imports.router)
    api.include_router(charges.router)
    api.include_router(billing.router)
    api.include_router(complaints.router)
    api.include_router(payments.router)
    api.include_router(compliance.router)
    api.include_router(home.router)
    api.include_router(internal_jobs.router)
    if settings.app_env == "local" and settings.supabase_jwt_secret:
        api.include_router(dev.router)

    app.include_router(api)
    return app


app = create_app()
