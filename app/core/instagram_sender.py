"""Envío de mensajes de texto vía Instagram Messaging API (Messenger Platform)."""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.facebook.com/v20.0"
_TIMEOUT = 10.0  # segundos


async def send_instagram_message(ig_user_id: str, recipient_igsid: str, text: str) -> None:
    """
    Envía un mensaje de texto al usuario vía Instagram Messaging API.

    Args:
        ig_user_id: ID de la cuenta de Instagram Business (la nuestra).
        recipient_igsid: IGSID del destinatario (Instagram-Scoped User ID).
        text: Texto a enviar (máx. 1000 caracteres según Meta).

    Requiere:
        INSTAGRAM_ACCESS_TOKEN con permiso instagram_manage_messages.
    """
    url = f"{_GRAPH_BASE}/{ig_user_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.instagram_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "recipient": {"id": recipient_igsid},
        "message": {"text": text[:1000]},   # Meta trunca silenciosamente; mejor explícito
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.is_success:
        data = response.json()
        msg_id = data.get("message_id", "unknown")
        logger.info("IG DM enviado a %s — message_id=%s", recipient_igsid, msg_id)
    else:
        logger.error(
            "Error al enviar IG DM a %s: HTTP %d — %s",
            recipient_igsid,
            response.status_code,
            response.text,
        )
        response.raise_for_status()
