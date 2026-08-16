"""Worker ARQ: procesa mensajes de WhatsApp de forma asíncrona."""
from __future__ import annotations

import logging
from typing import Any

from arq.connections import RedisSettings

from app.core.claude import call_claude
from app.core.config import settings
from app.core.whatsapp_sender import send_whatsapp_message
from app.db.connection import admin_conn, tenant_conn
from app.db.repos import conversations as conv_repo
from app.db.repos import messages as msg_repo
from app.db.repos import tenants as tenant_repo

logger = logging.getLogger(__name__)


def _extract_message(payload: dict) -> dict[str, Any] | None:
    """Extrae el primer mensaje del payload de WhatsApp Cloud API."""
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
        message = value["messages"][0]
        metadata = value["metadata"]
        contacts = value.get("contacts", [{}])
        return {
            "wamid": message["id"],
            "from_wa_id": message["from"],
            "phone_number_id": metadata["phone_number_id"],
            "contact_name": contacts[0].get("profile", {}).get("name"),
            "text": message.get("text", {}).get("body", ""),
            "msg_type": message.get("type", "text"),
        }
    except (KeyError, IndexError):
        return None


async def process_whatsapp_message(ctx: dict, payload: dict) -> None:
    """
    Flujo completo de procesamiento:
      1. Parsear payload WhatsApp
      2. Resolver tenant por phone_number_id (sin RLS)
      3. Upsert conversación
      4. Guardar mensaje entrante (idempotente por wamid)
      5. Obtener historial para contexto
      6. Llamar a Claude API con el historial
      7. Enviar respuesta al usuario vía WhatsApp Cloud API
      8. Guardar mensaje saliente en la BD
    """
    msg = _extract_message(payload)
    if not msg:
        logger.warning("Payload de WhatsApp sin mensaje extraíble")
        return

    # Solo texto por ahora
    if msg["msg_type"] != "text" or not msg["text"]:
        logger.info("Tipo '%s' ignorado (solo texto soportado)", msg["msg_type"])
        return

    wamid = msg["wamid"]
    logger.info("Procesando wamid=%s de %s", wamid, msg["from_wa_id"])

    # 1. Resolver tenant (admin_conn bypasea RLS)
    async with admin_conn() as conn:
        tenant = await tenant_repo.get_tenant_by_phone_number_id(
            conn, msg["phone_number_id"]
        )

    if not tenant:
        logger.error(
            "phone_number_id=%s no registrado en ningún tenant",
            msg["phone_number_id"],
        )
        return

    tenant_id = tenant["tenant_id"]
    phone_number_uuid = tenant["phone_number_uuid"]

    # 2-5. Operaciones con RLS del tenant
    async with tenant_conn(tenant_id) as conn:
        # Upsert conversación
        conversation = await conv_repo.get_or_create(
            conn,
            tenant_id=tenant_id,
            phone_number_uuid=phone_number_uuid,
            contact_wa_id=msg["from_wa_id"],
            contact_name=msg["contact_name"],
        )
        conversation_id = conversation["id"]

        # Guardar mensaje entrante (idempotente)
        saved = await msg_repo.save(
            conn,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            wamid=wamid,
            direction="inbound",
            role="user",
            content=msg["text"],
        )
        if saved is None:
            logger.info("Mensaje duplicado wamid=%s — ignorado", wamid)
            return

        # Historial para Claude
        history = await msg_repo.get_history(conn, conversation_id, limit=20)

    logger.info(
        "Conversación %s — %d mensajes en historial. Llamando a Claude.",
        conversation_id,
        len(history),
    )

    # 6. Llamar a Claude con el historial completo
    response_text = await call_claude(history)
    logger.info("Claude respondió para conversación %s", conversation_id)

    # 7. Enviar respuesta al usuario vía WhatsApp Cloud API
    await send_whatsapp_message(
        phone_number_id=msg["phone_number_id"],
        to_wa_id=msg["from_wa_id"],
        text=response_text,
    )

    # 8. Guardar mensaje saliente en la BD
    async with tenant_conn(tenant_id) as conn:
        await msg_repo.save(
            conn,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            wamid=None,          # los mensajes salientes no tienen wamid entrante
            direction="outbound",
            role="assistant",
            content=response_text,
        )


class WorkerSettings:
    functions = [process_whatsapp_message]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs: int = 10
    job_timeout: int = 300
    retry_jobs: bool = True
    max_tries: int = 3
    health_check_interval: int = 30
