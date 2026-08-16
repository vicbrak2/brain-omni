from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.webhook import router as webhook_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    # Future: pool de conexiones DB, Redis ping, etc.
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Brain Omni",
        description="Agente omnicanal IA para PYMEs chilenas",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.include_router(webhook_router, prefix="/webhook")

    @app.get("/health", tags=["infra"])
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": "0.1.0"})

    return app


app = create_app()
