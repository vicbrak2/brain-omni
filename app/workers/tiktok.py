"""Worker ARQ: procesa comentarios de TikTok de forma asíncrona.

Scope: EXTERNAL — Moderación de comentarios en videos de TikTok.

Flujo completo:
  1. Parsear payload del webhook de TikTok (comentario en video)
  2. Resolver tenant por tiktok_account_id
  3. Upsert conversación (usando video_id+comment_id como contexto)
  4. Guardar comentario entrante (idempotente por comment_id)
  5. Obtener historial de moderación del video
  6. Construir system prompt con SCOPE_HEADER + config del tenant + RAG
  7. Llamar a Brain (multi-LLM)
  8. Publicar respuesta al comentario vía TikTok API
  9. Guardar respuesta en historial

El SCOPE_HEADER de scope=external garantiza que el agente actúe
exclusivamente en moderación pública — sin acceso a analíticas internas.

Nota: TikTok webhooks requieren verificación HMAC de forma similar a Meta.
La verificación se realiza en el router webhook antes de encolar el job.
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.agent_prompts import build_system_prompt
from app.core.claude import call_claude
from app.core.embeddings import embed, vec_to_str
from app.core.scope import Channel, Scope
from app.core.tiktok_sender import reply_tiktok_comment
from app.db.connection import admin_conn, tenant_conn
from app.db.repos import agent_configs as agent_configs_repo
from app.db.repos import conversations as conv_repo
from app.db.repos import knowledge as knowledge_repo
from app.db.repos import messages as msg_repo

logger = logging.getLogger(__name__)

_CHANNEL = Channel.TIKTOK
_SCOPE   = Scope.EXTERNAL


def _extract_comment(payload: dict) -> dict[str, Any] | None:
    """
    Extrae el primer comentario de un payload de webhook de TikTok.

    Formato esperado (TikTok Event API):
    {
      "event":      "comment",
      "create_time": 1234567890,
      "content": {
        "comment_id":    "<id>",
        "video_id":      "<id>",
        "user_id":       "<commenter_user_id>",
        "username":      "<commenter_username>",
        "text":          "...",
        "tiktok_user_id": "<nuestra_cuenta>"
      }
    }

    Returns None si el payload no tiene un comentario procesable.
    """
    try:
        event_type = payload.get("event", "")
        if event_type != "comment":
            return None

        content = payload["content"]
        comment_id      = content["comment_id"]
        video_id        = content["video_id"]
        commenter_id    = content["user_id"]
        commenter_name  = content.get("username", "")
        text            = content.get("text", "").strip()
        tiktok_user_id  = content.get("tiktok_user_id", "")  # nuestra cuenta TikTok

        # No responder a nuestros propios comentarios
        if commenter_id == tiktok_user_id:
            return None

        return {
            "comment_id":     comment_id,
            "video_id":       video_id,
            "commenter_id":   commenter_id,
            "commenter_name": commenter_name,
            "text":           text,
            "tiktok_user_id": tiktok_user_id,
        }
    except (KeyError, TypeError):
        return None


async def process_tiktok_comment(ctx: dict, payload: dict) -> None:
    """
    Flujo completo de moderación de un comentario de TikTok.

    Scope: EXTERNAL — responde públicamente a comentarios en videos.
    """
    comment = _extract_comment(payload)
    if not comment:
        logger.warning("Payload de TikTok sin comentario procesable")
        return

    if not comment["text"]:
        logger.info("Comentario TikTok sin texto (emoji/sticker) — ignorado")
        return

    comment_id = comment["comment_id"]
    logger.info(
        "Procesando TikTok comment_id=%s en video=%s (scope=%s)",
        comment_id, comment["video_id"], _SCOPE.value,
    )

    # ── 2. Resolver tenant por tiktok_user_id ────────────────────────────────
    async with admin_conn() as conn:
        tenant = await conn.fetchrow(
            """
            SELECT
                t.id   AS tenant_id,
                ta.id  AS tt_account_uuid,
                ta.tiktok_user_id
            FROM tiktok_accounts ta
            JOIN tenants t ON t.id = ta.tenant_id
            WHERE ta.tiktok_user_id = $1
              AND ta.is_active       = TRUE
              AND t.is_active        = TRUE
            """,
            comment["tiktok_user_id"],
        )

    if not tenant:
        logger.error(
            "tiktok_user_id=%s no registrado en ningún tenant",
            comment["tiktok_user_id"],
        )
        return

    tenant_id      = str(tenant["tenant_id"])
    tt_account_uuid = str(tenant["tt_account_uuid"])

    # ── 3-5. Operaciones con RLS del tenant ──────────────────────────────────
    # Usamos video_id como "número de teléfono" (canal del video)
    # y commenter_id como contact_wa_id (identificador del comentador)
    async with tenant_conn(tenant_id) as conn:
        conversation = await conv_repo.get_or_create(
            conn,
            tenant_id=tenant_id,
            phone_number_uuid=tt_account_uuid,
            contact_wa_id=comment["commenter_id"],
            contact_name=comment["commenter_name"] or None,
        )
        conversation_id = conversation["id"]

        # Idempotente: comment_id como wamid
        saved = await msg_repo.save(
            conn,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            wamid=comment_id,
            direction="inbound",
            role="user",
            content=comment["text"],
        )
        if saved is None:
            logger.info("Comentario duplicado comment_id=%s — ignorado", comment_id)
            return

        # Historial de la conversación con este comentador en este video
        history = await msg_repo.get_history(conn, conversation_id, limit=10)

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

    # RAG: contexto de KB (útil para FAQs sobre el video/producto)
    rag_section: str | None = None
    async with admin_conn() as conn:
        has_kb = await knowledge_repo.tenant_has_embeddings(conn, tenant_id)

    if has_kb:
        query_emb = await embed(comment["text"])
        if query_emb is not None:
            async with admin_conn() as conn:
                chunks = await knowledge_repo.search_similar(
                    conn,
                    tenant_id=tenant_id,
                    query_embedding_str=vec_to_str(query_emb),
                    top_k=2,      # Respuestas TikTok son cortas — menos contexto
                    min_score=0.40,
                )
            if chunks:
                context_block = "\n\n---\n".join(c["chunk_text"] for c in chunks)
                rag_section = (
                    "\n\n## Contexto de la base de conocimiento\n"
                    f"{context_block}"
                )
                logger.info(
                    "RAG: %d chunks inyectados para TikTok conv %s",
                    len(chunks), conversation_id,
                )

    # SCOPE_HEADER siempre primero
    system_prompt = build_system_prompt(
        channel=_CHANNEL,
        scope=_SCOPE,
        custom_prompt=custom_prompt,
        rag_context=rag_section,
    )

    # Instrucción adicional: respuestas TikTok son cortas
    system_prompt += (
        "\n\nIMPORTANTE: Estás respondiendo un comentario de TikTok. "
        "Mantén la respuesta breve (máximo 3 oraciones) y usa un tono casual "
        "y cercano. Puedes usar 1-2 emojis relevantes."
    )

    logger.info(
        "TikTok conv %s — %d msgs, scope=%s/%s. Llamando a Brain.",
        conversation_id, len(history), _CHANNEL.value, _SCOPE.value,
    )

    # ── 7. Llamar a Brain ────────────────────────────────────────────────────
    response_text = await call_claude(history, system_prompt=system_prompt)
    logger.info("Brain respondió para TikTok conv %s", conversation_id)

    # ── 8. Publicar respuesta al comentario ───────────────────────────────────
    await reply_tiktok_comment(
        video_id=comment["video_id"],
        comment_id=comment_id,
        text=response_text,
    )

    # ── 9. Guardar respuesta en historial ────────────────────────────────────
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
