"""Queries para knowledge_docs y embeddings — ejecutar con admin_conn()."""
from __future__ import annotations

from typing import Any

import asyncpg


# ── knowledge_docs ────────────────────────────────────────────────────────────

async def list_docs(
    conn: asyncpg.Connection,
    tenant_id: str,
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT id, title, doc_type, is_active, created_at,
               (SELECT COUNT(*) FROM embeddings WHERE doc_id = knowledge_docs.id) AS chunks
        FROM knowledge_docs
        WHERE tenant_id = $1
        ORDER BY created_at DESC
        """,
        tenant_id,
    )
    return [dict(r) for r in rows]


async def create_doc(
    conn: asyncpg.Connection,
    tenant_id: str,
    title: str,
    content: str,
    doc_type: str = "custom",
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO knowledge_docs (tenant_id, title, content, doc_type)
        VALUES ($1, $2, $3, $4)
        RETURNING id, title, doc_type, is_active, created_at
        """,
        tenant_id,
        title,
        content,
        doc_type,
    )
    return dict(row)


async def delete_doc(
    conn: asyncpg.Connection,
    tenant_id: str,
    doc_id: str,
) -> None:
    await conn.execute(
        "DELETE FROM knowledge_docs WHERE id = $1 AND tenant_id = $2",
        doc_id,
        tenant_id,
    )


# ── embeddings ────────────────────────────────────────────────────────────────

async def save_chunk(
    conn: asyncpg.Connection,
    tenant_id: str,
    doc_id: str,
    chunk_index: int,
    chunk_text: str,
    embedding_str: str,          # formateado como "[0.1,0.2,...]"
) -> None:
    await conn.execute(
        """
        INSERT INTO embeddings
            (tenant_id, doc_id, chunk_index, chunk_text, embedding)
        VALUES ($1, $2, $3, $4, $5::vector)
        ON CONFLICT (doc_id, chunk_index)
        DO UPDATE SET chunk_text = EXCLUDED.chunk_text,
                      embedding  = EXCLUDED.embedding
        """,
        tenant_id,
        doc_id,
        chunk_index,
        chunk_text,
        embedding_str,
    )


async def search_similar(
    conn: asyncpg.Connection,
    tenant_id: str,
    query_embedding_str: str,    # formateado como "[0.1,0.2,...]"
    top_k: int = 3,
    min_score: float = 0.35,
) -> list[dict[str, Any]]:
    """Retorna los chunks más similares por coseno. min_score filtra ruido."""
    rows = await conn.fetch(
        """
        SELECT chunk_text,
               1 - (embedding <=> $2::vector) AS score
        FROM embeddings
        WHERE tenant_id = $1
          AND embedding IS NOT NULL
        ORDER BY embedding <=> $2::vector
        LIMIT $3
        """,
        tenant_id,
        query_embedding_str,
        top_k,
    )
    return [dict(r) for r in rows if r["score"] >= min_score]


async def tenant_has_embeddings(
    conn: asyncpg.Connection,
    tenant_id: str,
) -> bool:
    """Comprobación rápida: ¿hay embeddings para este tenant?"""
    val = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM embeddings WHERE tenant_id=$1 AND embedding IS NOT NULL)",
        tenant_id,
    )
    return bool(val)
