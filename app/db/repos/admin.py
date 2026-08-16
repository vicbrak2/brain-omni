"""Queries de administración — ejecutar siempre con admin_conn() (sin RLS)."""
from __future__ import annotations

from typing import Any

import asyncpg


async def list_tenants(conn: asyncpg.Connection) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT id, slug, name, plan, is_active, created_at
        FROM tenants
        ORDER BY name
        """
    )
    return [dict(r) for r in rows]


async def create_tenant(
    conn: asyncpg.Connection,
    slug: str,
    name: str,
    plan: str = "starter",
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO tenants (slug, name, plan)
        VALUES ($1, $2, $3)
        RETURNING id, slug, name, plan, is_active, created_at
        """,
        slug,
        name,
        plan,
    )
    return dict(row)


async def get_agent_config(
    conn: asyncpg.Connection,
    tenant_id: str,
) -> dict[str, Any]:
    """Retorna la config global del tenant (phone_number_id IS NULL)."""
    row = await conn.fetchrow(
        """
        SELECT system_prompt, temperature, max_tokens,
               handoff_enabled, handoff_threshold
        FROM agent_config
        WHERE tenant_id = $1 AND phone_number_id IS NULL
        LIMIT 1
        """,
        tenant_id,
    )
    if row:
        return dict(row)
    # Defaults si no existe aún
    return {
        "system_prompt": "",
        "temperature": 0.70,
        "max_tokens": 1024,
        "handoff_enabled": False,
        "handoff_threshold": 5,
    }


async def upsert_agent_config(
    conn: asyncpg.Connection,
    tenant_id: str,
    system_prompt: str,
    temperature: float,
    max_tokens: int,
    handoff_enabled: bool,
    handoff_threshold: int,
) -> None:
    """Crea o actualiza la config global del tenant.

    Requiere el índice parcial idx_agent_config_global de la migración 003.
    """
    await conn.execute(
        """
        INSERT INTO agent_config
            (tenant_id, system_prompt, temperature, max_tokens,
             handoff_enabled, handoff_threshold)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (tenant_id) WHERE phone_number_id IS NULL
        DO UPDATE SET
            system_prompt    = EXCLUDED.system_prompt,
            temperature      = EXCLUDED.temperature,
            max_tokens       = EXCLUDED.max_tokens,
            handoff_enabled  = EXCLUDED.handoff_enabled,
            handoff_threshold = EXCLUDED.handoff_threshold,
            updated_at       = NOW()
        """,
        tenant_id,
        system_prompt,
        temperature,
        max_tokens,
        handoff_enabled,
        handoff_threshold,
    )
