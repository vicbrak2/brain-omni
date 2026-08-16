"""Pool de conexiones asyncpg con soporte de RLS por tenant."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import AsyncIterator
from uuid import UUID

import asyncpg

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Registra codec JSONB en cada conexión nueva del pool."""
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def get_pool() -> asyncpg.Pool:
    """Retorna el pool singleton, creándolo la primera vez."""
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await asyncpg.create_pool(
                    dsn=settings.database_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=30,
                    init=_init_connection,
                )
                logger.info("Pool de base de datos creado")
    return _pool


async def close_pool() -> None:
    """Cierra el pool al apagar la app."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Pool de base de datos cerrado")


@contextlib.asynccontextmanager
async def admin_conn() -> AsyncIterator[asyncpg.Connection]:
    """
    Conexión sin tenant context — para resolver tenant a partir del
    phone_number_id de Meta. El rol superuser de Railway bypasea RLS.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


@contextlib.asynccontextmanager
async def tenant_conn(tenant_id: UUID | str) -> AsyncIterator[asyncpg.Connection]:
    """
    Conexión con RLS activo para el tenant dado.
    Todas las queries dentro del bloque solo ven filas de ese tenant.

    Ejemplo::

        async with tenant_conn(tenant_id) as conn:
            rows = await conn.fetch("SELECT * FROM conversations")
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "SET LOCAL app.current_tenant_id = $1",
                str(tenant_id),
            )
            yield conn
