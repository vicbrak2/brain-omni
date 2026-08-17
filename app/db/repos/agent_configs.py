"""Queries para la tabla agent_configs (scope-aware agent configuration).

Esta tabla reemplaza y extiende la legacy `agent_config` incorporando:
  - Diferenciación por canal (whatsapp, instagram, facebook, tiktok)
  - Diferenciación por scope (external, internal)
  - Soporte para parámetros de generación (temperature, max_tokens)
  - Configuración de escalación automática

Requiere conexión con admin_conn() para escrituras y resolución cross-tenant.
Para lecturas desde workers, también admin_conn() (RLS no aplica en workers
porque usan set_app_tenant() internamente).
"""
from __future__ import annotations

from typing import Any

import asyncpg


async def get_config(
    conn: asyncpg.Connection,
    tenant_id: str,
    channel: str,
    scope: str,
) -> dict[str, Any] | None:
    """
    Obtiene la configuración de un agente para (tenant, canal, scope).

    Returns None si no existe configuración personalizada;
    el caller debe aplicar el prompt default del módulo agent_prompts.
    """
    row = await conn.fetchrow(
        """
        SELECT
            id,
            tenant_id,
            channel,
            scope,
            system_prompt,
            temperature,
            max_tokens,
            escalation_channel,
            escalation_after_msgs,
            is_active,
            created_at,
            updated_at
        FROM agent_configs
        WHERE tenant_id = $1
          AND channel   = $2
          AND scope     = $3
          AND is_active = TRUE
        """,
        tenant_id,
        channel,
        scope,
    )
    return dict(row) if row else None


async def upsert_config(
    conn: asyncpg.Connection,
    tenant_id: str,
    channel: str,
    scope: str,
    *,
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    escalation_channel: str | None = None,
    escalation_after_msgs: int = 0,
    is_active: bool = True,
) -> dict[str, Any]:
    """
    Crea o actualiza la configuración de un agente.

    Usa ON CONFLICT para garantizar idempotencia en el par (tenant, canal, scope).
    """
    row = await conn.fetchrow(
        """
        INSERT INTO agent_configs (
            tenant_id,
            channel,
            scope,
            system_prompt,
            temperature,
            max_tokens,
            escalation_channel,
            escalation_after_msgs,
            is_active
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (tenant_id, channel, scope)
        DO UPDATE SET
            system_prompt         = EXCLUDED.system_prompt,
            temperature           = EXCLUDED.temperature,
            max_tokens            = EXCLUDED.max_tokens,
            escalation_channel    = EXCLUDED.escalation_channel,
            escalation_after_msgs = EXCLUDED.escalation_after_msgs,
            is_active             = EXCLUDED.is_active,
            updated_at            = NOW()
        RETURNING *
        """,
        tenant_id,
        channel,
        scope,
        system_prompt,
        temperature,
        max_tokens,
        escalation_channel,
        escalation_after_msgs,
        is_active,
    )
    return dict(row)


async def list_configs(
    conn: asyncpg.Connection,
    tenant_id: str,
    *,
    channel: str | None = None,
    scope: str | None = None,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Lista todas las configuraciones de agente de un tenant.

    Opcionalmente filtra por canal y/o scope.
    """
    conditions = ["tenant_id = $1"]
    params: list[Any] = [tenant_id]

    if channel:
        params.append(channel)
        conditions.append(f"channel = ${len(params)}")

    if scope:
        params.append(scope)
        conditions.append(f"scope = ${len(params)}")

    if active_only:
        conditions.append("is_active = TRUE")

    where = " AND ".join(conditions)
    rows = await conn.fetch(
        f"""
        SELECT
            id, tenant_id, channel, scope,
            system_prompt, temperature, max_tokens,
            escalation_channel, escalation_after_msgs,
            is_active, created_at, updated_at
        FROM agent_configs
        WHERE {where}
        ORDER BY channel, scope
        """,
        *params,
    )
    return [dict(r) for r in rows]


async def deactivate_config(
    conn: asyncpg.Connection,
    tenant_id: str,
    channel: str,
    scope: str,
) -> bool:
    """
    Desactiva (soft-delete) la configuración de un agente.

    Returns True si se desactivó, False si no existía.
    """
    result = await conn.execute(
        """
        UPDATE agent_configs
        SET is_active = FALSE, updated_at = NOW()
        WHERE tenant_id = $1
          AND channel   = $2
          AND scope     = $3
          AND is_active = TRUE
        """,
        tenant_id,
        channel,
        scope,
    )
    # result es "UPDATE N"
    return result.split()[-1] != "0"
