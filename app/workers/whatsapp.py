"""Worker ARQ para procesar mensajes de WhatsApp de forma asíncrona.

ARQ usa Redis como broker. Cada job se reintenta hasta `max_tries` veces
con backoff exponencial. Los jobs son idempotentes por diseño (wamid único).

Ejecutar el worker:
    arq app.workers.whatsapp.WorkerSettings
"""
import logging
from typing import Any

from arq.connections import RedisSettings

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Funciones de tarea (cada función es un job ARQ)
# ---------------------------------------------------------------------------
async def process_whatsapp_message(ctx: dict, payload: dict) -> None:
    """Procesa un evento de mensaje de WhatsApp.

    Args:
        ctx: contexto ARQ (incluye redis pool, job_id, etc.)
        payload: payload completo recibido desde Meta Webhooks
    """
    job_id: str = ctx.get("job_id", "unknown")

    try:
        # Extraer datos del mensaje
        entry = payload.get("entry", [])
        if not entry:
            logger.debug("[%s] Payload sin entry, ignorando", job_id)
            return

        changes = entry[0].get("changes", [])
        if not changes:
            return

        value: dict = changes[0].get("value", {})
        messages: list[dict] = value.get("messages", [])

        if not messages:
            # Puede ser un status de entrega / lectura — ignorar
            return

        msg = messages[0]
        wamid: str = msg.get("id", "")          # ID único del mensaje (idempotency key)
        phone: str = msg.get("from", "")        # Número del remitente
        msg_type: str = msg.get("type", "")     # text, image, audio, ...

        if msg_type != "text":
            logger.info("[%s] Tipo de mensaje no soportado: %s", job_id, msg_type)
            return

        text: str = msg.get("text", {}).get("body", "")

        logger.info(
            "[%s] Mensaje recibido — wamid=%s phone=%s texto=%r",
            job_id, wamid, phone, text[:80],
        )

        # -------------------------------------------------------------------
        # TODO Fase 2: Idempotency check
        # Si wamid ya existe en Redis/DB → return early
        # -------------------------------------------------------------------

        # -------------------------------------------------------------------
        # TODO Fase 2: Resolver tenant
        # tenant_id = await resolver_tenant(phone)
        # -------------------------------------------------------------------

        # -------------------------------------------------------------------
        # TODO Fase 3: Llamar al agente IA (LiteLLM → Claude)
        # respuesta = await llamar_agente(tenant_id, phone, text)
        # -------------------------------------------------------------------

        # -------------------------------------------------------------------
        # TODO Fase 2: Enviar respuesta por WhatsApp Cloud API
        # await enviar_whatsapp(phone, respuesta)
        # -------------------------------------------------------------------

        logger.info("[%s] Job procesado OK — wamid=%s", job_id, wamid)

    except Exception as exc:
        logger.error("[%s] Error procesando mensaje: %s", job_id, exc, exc_info=True)
        raise  # ARQ reintentará según max_tries


# ---------------------------------------------------------------------------
# Configuración del worker ARQ
# ---------------------------------------------------------------------------
class WorkerSettings:
    """Configuración leída por `arq` al arrancar el worker."""

    functions: list[Any] = [process_whatsapp_message]

    redis_settings: RedisSettings = RedisSettings.from_dsn(settings.redis_url)

    # Concurrencia y timeouts
    max_jobs: int = 10           # jobs paralelos por instancia
    job_timeout: int = 300       # segundos antes de cancelar un job

    # Reintentos
    retry_jobs: bool = True
    max_tries: int = 3

    # Health check
    health_check_interval: int = 30
