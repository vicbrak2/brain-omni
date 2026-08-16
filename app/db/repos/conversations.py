"""Queries de conversaciones."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg


async def get_or_create(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID | str,
    phone_number_uuid: UUID | str,
    contact_wa_id: str,
    contact_name: str | None = None,
) -> dict[str, Any]:
    """
    Retorna la conversación existente o crea una nueva.
    UPSERT atómico — seguro ante reintentos concurrentes.
    """
    row = await conn.fetchrow(
        """
        INSERT INTO conversations
            (tenant_id, phone_number_id, contact_wa_id, contact_name)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (tenant_id, phone_number_id, contact_wa_id)
        DO UPDATE SET
            contact_name = COALESCE(EXCLUDED.contact_name, conversations.contact_name),
            updated_at   = NOW()
        RETURNING *
        """,
        str(tenant_id),
        str(phone_number_uuid),
        contact_wa_id,
        contact_name,
    )
    return dict(row)  # type: ignore[arg-type]


async def update_status(
    conn: asyncpg.Connection,
    conversation_id: UUID | str,
    status: str,
) -> None:
    """Actualiza el estado de la conversación (bot/open/human/resolved)."""
    await conn.execute(
        "UPDATE conversations SET status = $1 WHERE id = $2",
        status,
        str(conversation_id),
    )
