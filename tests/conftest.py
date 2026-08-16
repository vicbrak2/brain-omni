"""Configuración mínima para correr tests sin .env ni servicios externos.

Stubbea los módulos de infraestructura (arq, asyncpg, redis) que no se
pueden importar en el entorno de CI/test sin los servicios corriendo.
Los tests unitarios nunca los usan directamente; el stub solo evita el
ImportError en la fase de colección de pytest.
"""
import os
import sys
from unittest.mock import MagicMock

# ── Env vars mínimas ──────────────────────────────────────────────────────────
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "test-token")
os.environ.setdefault("WHATSAPP_APP_SECRET", "test-secret-32-chars-minimum-pad")
os.environ.setdefault("INSTAGRAM_VERIFY_TOKEN", "test-ig-token")
os.environ.setdefault("INSTAGRAM_APP_SECRET", "test-ig-secret-32-chars-pad-00000")
os.environ.setdefault("INSTAGRAM_ACCESS_TOKEN", "test-ig-access")

# ── Stubs de infraestructura ──────────────────────────────────────────────────
# arq y asyncpg no pueden importarse sin cffi/libpq en el entorno de test.
# Los stubs permiten colectar los módulos de app sin errores; los tests
# unitarios solo ejercen lógica pura (parsers, HMAC) sin tocar estos.
for _mod in (
    "arq",
    "arq.connections",
    "asyncpg",
    "redis",
    "redis.asyncio",
):
    sys.modules.setdefault(_mod, MagicMock())
