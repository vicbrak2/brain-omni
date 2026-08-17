"""Worker ARQ: procesa mensajes de Facebook Messenger (DMs) de forma asíncrona.

Scope: EXTERNAL — Soporte al cliente vía Facebook Messenger.

Flujo completo:
  1. Parsear payload de Facebook Messenger webhook
  2. Resolver tenant por page_id (nuestra Facebook Page)
  3. Upsert conversación
  4. Guardar mensaje entrante (idempotente por mid)
  5. Obtener historial para contexto
  6. Construir system prompt con SCOPE_HEADER + config del tenant + RAG
  7. Llamar a Brain (multi-LLM)
  8. Enviar respuesta vía Facebook Messenger Graph API
  9. Guardar mensaje saliente

El SCOPE_HEADER de scope=external garantiza que el agente no pueda
acceder a analíticas ni a conversaciones de otros usuarios.
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.agent_prompts import build_system_prompt
from app.core.claude import call_claude
from app.core.embeddings import embed, vec_to_str
from app.core.facebook_sender import send_facebook_message
from app.core.scope import Channel, Scope
from app.db.connection import admin_conn, tenant_conn
from app.db.repos import agent_configs as agent_configs_repo
from app.db.repos import conversations as conv_repo
from app.db.repos import knowledge as knowledge_repo
from app.db.repos import messages as msg_repo

logger = logging.getLogger(__name__)

_CHANNEL = Channel.FACEBOOK
_SCOPE   = Scope.EXTERNAL


def _extract_messenger_event(payload: dict) -> dict[str, Any] | None:
    """
    Extrae el primer mensaje de un payload de Facebook Messenger webhook.

    Formato Meta (Messenger Platform):
    {
      "entry": [{
        "id": "<page_id>",
        "messaging": [{
          "sender": {"id": "<sender_psid>"},
          "recipient": {"id": "<page_id>"},
          "message": {"mid": "...", "text": "..."}
        }]
      }]
    }

    Returns None si el payload no contiene un mensaje procesable.
    """
    try:
        entry   = payload["entry"][0]
        page_id = entry["id"]                  # nuestra Facebook Page ID
        event   = entry["messaging"][0]
        sender_psid = event["sender"]["id"]

        # Ignorar eco: mensajes que nosotros mismos enviamos
        if sender_psid == page_id:
            return None

        # Ignorar delivery/read confirmations (no tienen .message)
        message = event.get("message")
        if not message:
            return None

        # Ignorar ecos del servidor (is_echo)
        if message.get("is_echo"):
            return None

        mid  = message.get("mid", "")
        text = message.get("text", "").strip()

        return {
            "mid":         mid,
            "page_id":     page_id,
            "sender_psid": sender_psid,
            "text":        text,
        }
    except (KeyError, IndexError):
        return None


async def process_facebook_message(ctx: dict, payload: dict) -> None:
    """
    Flujo completo de procesamiento de un mensaje de Facebook Messenger.

    Scope: EXTERNAL — responde a mensajes de clientes/seguidores.
    """
    event = _extract_messenger_event(payload)
    if not event:
        logger.warning("Payload de Facebook sin mensaje Messenger extraíble")
        return

    if not event["text"]:
        logger.info("Mensaje FB Messenger sin texto (adjunto/sticker) — ignorado")
        return

    mid = event["mid"]
    logger.info(
        "Procesando FB Messenger mid=%s de psid=%s (scope=%s)",
        mid, event["sender_psid"], _SCOPE.value,
    )

    # ── 2. Resolver tenant por page_id ──────────────────────────────────────
    async with admin_conn() as conn:
        tenant = await conn.fetchrow(
            """
            SELECT
                t.id   AS tenant_id,
                fa.id  AS fb_account_uuid,
                fa.page_id
            FROM facebook_accounts fa
            JOIN tenants t ON t.id = fa.tenant_id
            WHERE fa.page_id  = $1
              AND fa.is_active = TRUE
              AND t.is_active  = TRUE
            """,
            event["page_id"],
        )

    if not tenant:
        logger.error(
            "page_id=%s no registrado en ningún tenant", event["page_id"]
        )
        return

    tenant_id      = str(tenant["tenant_id"])
    fb_account_uuid = str(tenant["fb_account_uuid"])

    # ── 3-5. Operaciones con RLS del tenant ─────────────────────────────────
    async with tenant_conn(tenant_id) as conn:
        conversation = await conv_repo.get_or_create(
            conn,
            tenant_id=tenant_id,
            phone_number_uuid=fb_account_uuid,
            contact_wa_id=event["sender_psid"],
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
            content=event["text"],
        )
        if saved is None:
            logger.info("Mensaje duplicado mid=%s — ignorado", mid)
            return

        history = await msg_repo.get_history(conn, conversation_id, limit=20)

    # ── 6. Construir system prompt con scope enforcement ─────────────────────
    async with admin_conn() as conn:
        agent_cfg = await agent_configs_repo.get_config(
            conn, tenant_id, _CHANNEL.value, _SCOPE.value
        )

    custom_prompt = (
        agent_cfg["system_prompt"]
        if agent_cfg and agent_cfg.get("system_prompt")
        else None
    )

    # RAG: enriquecer con contexto de la knowledge base
    rag_section: str | None = None
    async with admin_conn() as conn:
        has_kb = await knowledge_repo.tenant_has_embeddings(conn, tenant_id)

    if has_kb:
        query_emb = await embed(event["text"])
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
                logger.info(
                    "RAG: %d chunks inyectados para FB conv %s",
                    len(chunks), conversation_id,
                )

    # SCOPE_HEADER siempre primero — no puede ser sobreescrito por el tenant
    system_prompt = build_system_prompt(
        channel=_CHANNEL,
        scope=_SCOPE,
        custom_prompt=custom_prompt,
        rag_context=rag_section,
    )

    logger.info(
        "FB conv %s — %d msgs, scope=%s/%s. Llamando a Brain.",
        conversation_id, len(history), _CHANNEL.value, _SCOPE.value,
    )

    # ── 7. Llamar a Brain ────────────────────────────────────────────────────
    response_text = await call_claude(history, system_prompt=system_prompt)
    logger.info("Brain respondió para FB conv %s", conversation_id)

    # ── 8. Enviar respuesta vía Messenger ────────────────────────────────────
    await send_facebook_message(
        page_id=event["page_id"],
        recipient_psid=event["sender_psid"],
        text=response_text,
    )

    # ── 9. Guardar mensaje saliente ───────────────────────────────────────────
    async with tenant_conn(tenant_id) as conn:
        await msg_repo.save(
            conn,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            wamid=None,
            direction="outbound",
            role="assistant",
            content=response_text,
        )
