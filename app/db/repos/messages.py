"""Queries de mensajes."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg


async def save(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID | str,
    conversation_id: UUID | str,
    wamid: str | None,
    direction: str,       # "inbound" | "outbound"
    role: str,            # "user" | "assistant" | "system"
    content: str,
    content_type: str = "text",
    metadata: dict | None = None,
) -> dict[str, Any] | None:
    """
    Guarda un mensaje. Retorna None si wamid ya existe (idempotencia).
    El UNIQUE(wamid) garantiza que WhatsApp no pueda duplicar mensajes
    aunque reintente el webhook.
    """
    row = await conn.fetchrow(
        """
        INSERT INTO messages
            (tenant_id, conversation_id, wamid, direction, role,
             content_type, content, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (wamid) DO NOTHING
        RETURNING *
        """,
        str(tenant_id),
        str(conversation_id),
        wamid,
        direction,
        role,
        content_type,
        content,
        metadata or {},
    )
    return dict(row) if row else None


async def get_history(
    conn: asyncpg.Connection,
    conversation_id: UUID | str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Retorna los últimos `limit` mensajes de texto de la conversación,
    ordenados cronológicamente (más antiguo primero).
    Formato listo para pasar a la API de Claude como `messages`.
    """
    rows = await conn.fetch(
        """
        SELECT role, content, created_at
        FROM messages
        WHERE conversation_id = $1
          AND content_type    = 'text'
          AND role IN ('user', 'assistant')
        ORDER BY created_at ASC
        LIMIT $2
        """,
        str(conversation_id),
        limit,
    )
    return [dict(r) for r in rows]
