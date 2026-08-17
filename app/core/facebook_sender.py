"""Envío de mensajes de texto vía Facebook Messenger (Graph API).

Facebook Messenger usa el mismo endpoint de Graph API que Instagram,
pero con el Page Access Token (no el Instagram Access Token) y contra
el page_id en lugar del ig_user_id.

Referencia: https://developers.facebook.com/docs/messenger-platform/send-messages
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.facebook.com/v20.0"
_TIMEOUT = 10.0  # segundos
_MAX_TEXT_LEN = 2000  # Messenger permite hasta 2000 caracteres por mensaje


async def send_facebook_message(page_id: str, recipient_psid: str, text: str) -> None:
    """
    Envía un mensaje de texto al usuario vía Facebook Messenger (Graph API).

    Args:
        page_id: ID de la Facebook Page del negocio.
        recipient_psid: Page-Scoped User ID del destinatario.
        text: Texto a enviar (máx. 2000 caracteres).

    Requiere:
        FACEBOOK_ACCESS_TOKEN con permiso pages_messaging.
    """
    url = f"{_GRAPH_BASE}/{page_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.facebook_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "recipient": {"id": recipient_psid},
        "message": {"text": text[:_MAX_TEXT_LEN]},
        "messaging_type": "RESPONSE",   # Respuesta a un mensaje del usuario
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.is_success:
        data = response.json()
        msg_id = data.get("message_id", "unknown")
        logger.info(
            "FB Messenger enviado a psid=%s — message_id=%s",
            recipient_psid,
            msg_id,
        )
    else:
        logger.error(
            "Error al enviar FB Messenger a psid=%s: HTTP %d — %s",
            recipient_psid,
            response.status_code,
            response.text,
        )
        response.raise_for_status()
