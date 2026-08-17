"""API de administración — CRUD de tenants y configuración del agente.

Protegida con Bearer token (ADMIN_API_TOKEN en env).
Todos los endpoints usan admin_conn() para saltear RLS.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.db.connection import admin_conn
from app.db.repos import admin as admin_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Auth ──────────────────────────────────────────────────────────────────────

def _require_token(authorization: str | None = Header(default=None)) -> None:
    if not settings.admin_api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_TOKEN no configurado en el servidor",
        )
    if authorization != f"Bearer {settings.admin_api_token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de administración inválido",
        )


Auth = Depends(_require_token)


# ── Schemas ───────────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    slug: str = Field(..., min_length=2, max_length=60, pattern=r"^[a-z0-9-]+$")
    plan: str = Field("starter", pattern=r"^(free|starter|pro|enterprise)$")


class AgentConfigIn(BaseModel):
    system_prompt: str = Field("", max_length=8000)
    temperature: float = Field(0.70, ge=0.0, le=1.0)
    max_tokens: int = Field(1024, ge=64, le=4096)
    handoff_enabled: bool = False
    handoff_threshold: int = Field(5, ge=1, le=50)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/tenants")
async def list_tenants(_: None = Auth) -> list[dict]:
    async with admin_conn() as conn:
        return await admin_repo.list_tenants(conn)


@router.post("/tenants", status_code=status.HTTP_201_CREATED)
async def create_tenant(body: TenantCreate, _: None = Auth) -> dict:
    async with admin_conn() as conn:
        try:
            return await admin_repo.create_tenant(
                conn, slug=body.slug, name=body.name, plan=body.plan
            )
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El slug '{body.slug}' ya existe",
                )
            raise


@router.get("/tenants/{tenant_id}/config")
async def get_config(tenant_id: str, _: None = Auth) -> dict:
    async with admin_conn() as conn:
        return await admin_repo.get_agent_config(conn, tenant_id)


@router.put("/tenants/{tenant_id}/config", status_code=status.HTTP_200_OK)
async def upsert_config(
    tenant_id: str,
    body: AgentConfigIn,
    _: None = Auth,
) -> dict:
    async with admin_conn() as conn:
        await admin_repo.upsert_agent_config(
            conn,
            tenant_id=tenant_id,
            system_prompt=body.system_prompt,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            handoff_enabled=body.handoff_enabled,
            handoff_threshold=body.handoff_threshold,
        )
    return {"status": "saved"}
