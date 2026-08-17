"""Worker ARQ: procesa mensajes directos de Instagram (DMs) de forma asíncrona.

Flujo completo:
  1. Parsear payload de Instagram Messaging API (webhook `messaging`)
  2. Resolver tenant por ig_user_id (el ID de nuestra cuenta IG Business)
  3. Upsert conversación (reutiliza tabla conversations; ig_user_id → phone_number_id)
  4. Guardar mensaje entrante (idempotente por mid)
  5. Obtener historial para contexto
  6. Llamar a Brain (multi-LLM con rotación dinámica)
  7. Enviar respuesta al usuario vía Instagram Messaging API
  8. Guardar mensaje saliente en la BD
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.claude import call_claude
from app.core.embeddings import embed, vec_to_str
from app.core.instagram_sender import send_instagram_message
from app.db.connection import admin_conn, tenant_conn
from app.db.repos import conversations as conv_repo
from app.db.repos import knowledge as knowledge_repo
from app.db.repos import messages as msg_repo
from app.db.repos import tenants as tenant_repo

logger = logging.getLogger(__name__)


def _extract_dm(payload: dict) -> dict[str, Any] | None:
    """
    Extrae el primer DM del payload de Instagram Messaging webhook.

    Formato Meta (Messenger Platform para Instagram):
    {
      "entry": [{
        "id": "<ig_user_id>",
        "messaging": [{
          "sender": {"id": "<sender_igsid>"},
          "recipient": {"id": "<ig_user_id>"},
          "message": {"mid": "...", "text": "..."}
        }]
      }]
    }
    """
    try:
        entry = payload["entry"][0]
        ig_user_id = entry["id"]              # nuestra cuenta IG Business
        event = entry["messaging"][0]
        sender_igsid = event["sender"]["id"]

        # Ignorar eco: mensajes que nosotros mismos enviamos
        if sender_igsid == ig_user_id:
            return None

        message = event.get("message", {})
        mid = message.get("mid", "")
        text = message.get("text", "").strip()

        return {
            "mid": mid,
            "ig_user_id": ig_user_id,
            "sender_igsid": sender_igsid,
            "text": text,
        }
    except (KeyError, IndexError):
        return None


async def process_instagram_message(ctx: dict, payload: dict) -> None:
    """
    Flujo completo de procesamiento de un DM de Instagram.

    1. Parsear payload Instagram
    2. Resolver tenant por ig_user_id (sin RLS)
    3. Upsert conversación
    4. Guardar mensaje entrante (idempotente por mid)
    5. Obtener historial para contexto
    6. Llamar a Brain (multi-LLM con rotación dinámica)
    7. Enviar respuesta al usuario vía Instagram Messaging API
    8. Guardar mensaje saliente en la BD
    """
    dm = _extract_dm(payload)
    if not dm:
        logger.warning("Payload de Instagram sin DM extraíble")
        return

    if not dm["text"]:
        logger.info("DM sin texto (sticker/media) — ignorado")
        return

    mid = dm["mid"]
    logger.info("Procesando IG DM mid=%s de %s", mid, dm["sender_igsid"])

    # 2. Resolver tenant por ig_user_id (admin_conn bypasea RLS)
    async with admin_conn() as conn:
        tenant = await tenant_repo.get_tenant_by_ig_user_id(conn, dm["ig_user_id"])

    if not tenant:
        logger.error(
            "ig_user_id=%s no registrado en ningún tenant", dm["ig_user_id"]
        )
        return

    tenant_id = tenant["tenant_id"]
    ig_account_uuid = tenant["ig_account_uuid"]

    # 3-5. Operaciones con RLS del tenant
    async with tenant_conn(tenant_id) as conn:
        # Upsert conversación (phone_number_id → ig_account_uuid, contact_wa_id → sender_igsid)
        conversation = await conv_repo.get_or_create(
            conn,
            tenant_id=tenant_id,
            phone_number_uuid=ig_account_uuid,
            contact_wa_id=dm["sender_igsid"],
            contact_name=None,
        )
        conversation_id = conversation["id"]

        # Guardar mensaje entrante (idempotente por mid)
        saved = await msg_repo.save(
            conn,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            wamid=mid,
            direction="inbound",
            role="user",
            content=dm["text"],
        )
        if saved is None:
            logger.info("Mensaje duplicado mid=%s — ignorado", mid)
            return

        # Historial para Brain
        history = await msg_repo.get_history(conn, conversation_id, limit=20)

        # Configuración del agente (system prompt del tenant, sin phone_number_id)
        agent_cfg = await tenant_repo.get_agent_config(conn, tenant_id, None)

    system_prompt = (
        agent_cfg["system_prompt"]
        if agent_cfg and agent_cfg.get("system_prompt")
        else None
    )

    # RAG: enriquecer el system prompt con contexto de la base de conocimiento
    async with admin_conn() as conn:
        has_kb = await knowledge_repo.tenant_has_embeddings(conn, tenant_id)

    if has_kb:
        query_emb = await embed(dm["text"])
        if query_emb is not None:
            async with admin_conn() as conn:
                chunks = await knowledge_repo.search_similar(
                    conn,
                    tenant_id=tenant_id,
                    query_embedding_str=vec_to_str(query_emb),
                    top_k=3,
                    min_score=0.35,
                )
            if chunks:
                context_block = "\n\n---\n".join(c["chunk_text"] for c in chunks)
                rag_section = (
                    "\n\n## Contexto de la base de conocimiento\n"
                    f"{context_block}"
                )
                system_prompt = (system_prompt or "") + rag_section
                logger.info(
                    "RAG: %d chunks inyectados para IG conversación %s",
                    len(chunks),
                    conversation_id,
                )

    logger.info(
        "IG conversación %s — %d msgs, system_prompt=%s. Llamando a Brain.",
        conversation_id,
        len(history),
        "custom" if system_prompt else "default",
    )

    # 6. Llamar a Brain con el system prompt del tenant
    response_text = await call_claude(history, system_prompt=system_prompt)
    logger.info("Brain respondió para IG conversación %s", conversation_id)

    # 7. Enviar respuesta al usuario vía Instagram Messaging API
    await send_instagram_message(
        ig_user_id=dm["ig_user_id"],
        recipient_igsid=dm["sender_igsid"],
        text=response_text,
    )

    # 8. Guardar mensaje saliente en la BD
    async with tenant_conn(tenant_id) as conn:
        await msg_repo.save(
            conn,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            wamid=None,           # mensajes salientes no tienen mid entrante
            direction="outbound",
            role="assistant",
            content=response_text,
        )
