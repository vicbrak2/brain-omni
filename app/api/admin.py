"""API de administración — CRUD de tenants y configuración del agente.

Protegida con Bearer token (ADMIN_API_TOKEN en env).
Todos los endpoints usan admin_conn() para saltear RLS.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.core.agent_prompts import get_scope_header
from app.core.config import settings
from app.core.embeddings import chunk_text, embed_chunks, vec_to_str
from app.core.scope import Channel, Scope
from app.db.connection import admin_conn
from app.db.repos import admin as admin_repo
from app.db.repos import agent_configs as agent_configs_repo
from app.db.repos import knowledge as knowledge_repo

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


class DocCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=10, max_length=50_000)
    doc_type: str = Field("custom", pattern=r"^(faq|product|policy|custom)$")


class AgentScopeConfigIn(BaseModel):
    """Config de un agente para un (canal, scope) específico."""
    system_prompt: str | None = Field(None, max_length=8000,
        description="Custom prompt del tenant. None = usar template default.")
    temperature: float | None = Field(None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(None, ge=64, le=4096)
    escalation_channel: str | None = Field(None,
        pattern=r"^(whatsapp|instagram|facebook|tiktok|human)$")
    escalation_after_msgs: int = Field(0, ge=0, le=50)


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


# ── Agent scope configs ───────────────────────────────────────────────────────

_VALID_CHANNELS = {c.value for c in Channel}
_VALID_SCOPES   = {s.value for s in Scope}


@router.get("/tenants/{tenant_id}/agents")
async def list_agent_configs(tenant_id: str, _: None = Auth) -> list[dict]:
    """Lista todas las configuraciones de agentes del tenant (todos los canales y scopes)."""
    async with admin_conn() as conn:
        configs = await agent_configs_repo.list_configs(conn, tenant_id, active_only=False)
    # Agregar scope_header_preview para cada config
    for cfg in configs:
        cfg["scope_header"] = get_scope_header(cfg["channel"], cfg["scope"])
    return configs


@router.get("/tenants/{tenant_id}/agents/{channel}/{scope}")
async def get_agent_config_by_scope(
    tenant_id: str, channel: str, scope: str, _: None = Auth
) -> dict:
    """Obtiene la config de un agente para (tenant, canal, scope)."""
    if channel not in _VALID_CHANNELS:
        raise HTTPException(status_code=400, detail=f"Canal inválido: {channel}")
    if scope not in _VALID_SCOPES:
        raise HTTPException(status_code=400, detail=f"Scope inválido: {scope}")

    async with admin_conn() as conn:
        cfg = await agent_configs_repo.get_config(conn, tenant_id, channel, scope)

    return {
        "tenant_id":    tenant_id,
        "channel":      channel,
        "scope":        scope,
        "system_prompt":      cfg["system_prompt"] if cfg else None,
        "temperature":        cfg["temperature"]   if cfg else None,
        "max_tokens":         cfg["max_tokens"]    if cfg else None,
        "escalation_channel": cfg.get("escalation_channel") if cfg else None,
        "escalation_after_msgs": cfg["escalation_after_msgs"] if cfg else 0,
        "scope_header": get_scope_header(channel, scope),   # siempre incluido (read-only)
    }


@router.put("/tenants/{tenant_id}/agents/{channel}/{scope}")
async def upsert_agent_config_by_scope(
    tenant_id: str,
    channel: str,
    scope: str,
    body: AgentScopeConfigIn,
    _: None = Auth,
) -> dict:
    """Crea o actualiza la config de un agente para (tenant, canal, scope)."""
    if channel not in _VALID_CHANNELS:
        raise HTTPException(status_code=400, detail=f"Canal inválido: {channel}")
    if scope not in _VALID_SCOPES:
        raise HTTPException(status_code=400, detail=f"Scope inválido: {scope}")

    # Los agentes internos no pueden escalar
    if scope == Scope.INTERNAL.value and body.escalation_channel:
        raise HTTPException(
            status_code=400,
            detail="Los agentes internos no pueden tener canal de escalación",
        )

    async with admin_conn() as conn:
        await agent_configs_repo.upsert_config(
            conn,
            tenant_id=tenant_id,
            channel=channel,
            scope=scope,
            system_prompt=body.system_prompt,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            escalation_channel=body.escalation_channel,
            escalation_after_msgs=body.escalation_after_msgs,
        )
    return {"status": "saved", "channel": channel, "scope": scope}


# ── Knowledge docs ────────────────────────────────────────────────────────────

@router.get("/tenants/{tenant_id}/docs")
async def list_docs(tenant_id: str, _: None = Auth) -> list[dict]:
    async with admin_conn() as conn:
        return await knowledge_repo.list_docs(conn, tenant_id)


@router.post("/tenants/{tenant_id}/docs", status_code=status.HTTP_201_CREATED)
async def create_doc(tenant_id: str, body: DocCreate, _: None = Auth) -> dict:
    """Crea el documento, lo divide en chunks y genera embeddings."""
    async with admin_conn() as conn:
        doc = await knowledge_repo.create_doc(
            conn,
            tenant_id=tenant_id,
            title=body.title,
            content=body.content,
            doc_type=body.doc_type,
        )

    # Chunking + embedding (fuera del pool para no bloquear)
    chunks = chunk_text(body.content)
    embeddings = await embed_chunks(chunks)

    embedded = 0
    async with admin_conn() as conn:
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            if emb is not None:
                await knowledge_repo.save_chunk(
                    conn,
                    tenant_id=tenant_id,
                    doc_id=str(doc["id"]),
                    chunk_index=idx,
                    chunk_text=chunk,
                    embedding_str=vec_to_str(emb),
                )
                embedded += 1

    logger.info(
        "Doc '%s' creado: %d chunks, %d embeddings generados",
        body.title, len(chunks), embedded,
    )
    return {**doc, "chunks": len(chunks), "embedded": embedded}


@router.delete("/tenants/{tenant_id}/docs/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doc(tenant_id: str, doc_id: str, _: None = Auth) -> Response:
    async with admin_conn() as conn:
        await knowledge_repo.delete_doc(conn, tenant_id=tenant_id, doc_id=doc_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
