import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.admin import router as admin_router
from app.api.webhook import router as webhook_router
from app.core.config import settings
from app.db.connection import close_pool, get_pool

logger = logging.getLogger(__name__)

VERSION = "0.4.0"

_STATUS_PAGE = Path(__file__).parent / "app" / "static" / "status.html"
_PANEL_PAGE  = Path(__file__).parent / "app" / "static" / "panel.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown del pool de base de datos."""
    try:
        await get_pool()
    except Exception as exc:  # noqa: BLE001
        logger.warning("BD no disponible al iniciar: %s", exc)
    yield
    await close_pool()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Brain Omni",
        description="Agente omnicanal IA para PYMEs chilenas",
        version=VERSION,
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.include_router(webhook_router, prefix="/webhook")
    app.include_router(admin_router)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def status_ui() -> HTMLResponse:
        """Panel de estado del proyecto — sirve la UI estática."""
        return HTMLResponse(_STATUS_PAGE.read_text(encoding="utf-8"))

    @app.get("/panel", response_class=HTMLResponse, include_in_schema=False)
    async def admin_panel() -> HTMLResponse:
        """Panel de configuración de tenants y agentes."""
        return HTMLResponse(_PANEL_PAGE.read_text(encoding="utf-8"))

    @app.get("/health", tags=["infra"])
    async def health() -> JSONResponse:
        db_status = "ok"
        try:
            pool = await get_pool()
            await pool.fetchval("SELECT 1")
        except Exception as exc:  # noqa: BLE001
            db_status = f"error: {exc}"

        status = "ok" if db_status == "ok" else "degraded"
        code = 200 if status == "ok" else 503
        return JSONResponse(
            {"status": status, "version": VERSION, "db": db_status},
            status_code=code,
        )

    return app


app = create_app()
