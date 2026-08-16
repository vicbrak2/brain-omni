"""Queries relacionadas con tenants y configuración del agente."""
from __future__ import annotations

from typing import Any

import asyncpg


async def get_tenant_by_phone_number_id(
    conn: asyncpg.Connection,
    phone_number_id: str,
) -> dict[str, Any] | None:
    """
    Resuelve el tenant a partir del phone_number_id de Meta.
    Debe ejecutarse con admin_conn() — sin RLS activo.
    """
    row = await conn.fetchrow(
        """
        SELECT
            t.id               AS tenant_id,
            t.slug             AS tenant_slug,
            t.name             AS tenant_name,
            t.plan             AS tenant_plan,
            pn.id              AS phone_number_uuid,
            pn.phone_number_id AS phone_number_id,
            pn.display_number  AS display_number
        FROM phone_numbers pn
        JOIN tenants t ON t.id = pn.tenant_id
        WHERE pn.phone_number_id = $1
          AND pn.is_active = TRUE
          AND t.is_active  = TRUE
        """,
        phone_number_id,
    )
    return dict(row) if row else None


async def get_tenant_by_ig_user_id(
    conn: asyncpg.Connection,
    ig_user_id: str,
) -> dict[str, Any] | None:
    """
    Resuelve el tenant a partir del ig_user_id de nuestra cuenta IG Business.
    Requiere la tabla instagram_accounts (migración pendiente).
    Debe ejecutarse con admin_conn() — sin RLS activo.
    """
    row = await conn.fetchrow(
        """
        SELECT
            t.id               AS tenant_id,
            t.slug             AS tenant_slug,
            t.name             AS tenant_name,
            ia.id              AS ig_account_uuid,
            ia.ig_user_id      AS ig_user_id
        FROM instagram_accounts ia
        JOIN tenants t ON t.id = ia.tenant_id
        WHERE ia.ig_user_id = $1
          AND ia.is_active   = TRUE
          AND t.is_active    = TRUE
        """,
        ig_user_id,
    )
    return dict(row) if row else None


async def get_agent_config(
    conn: asyncpg.Connection,
    tenant_id: str,
    phone_number_uuid: str | None = None,
) -> dict[str, Any] | None:
    """
    Retorna la configuración del agente con prioridad:
    config específica del número > config global del tenant.
    """
    row = await conn.fetchrow(
        """
        SELECT *
        FROM agent_config
        WHERE tenant_id = $1
          AND (phone_number_id = $2 OR phone_number_id IS NULL)
        ORDER BY phone_number_id NULLS LAST
        LIMIT 1
        """,
        tenant_id,
        phone_number_uuid,
    )
    return dict(row) if row else None
