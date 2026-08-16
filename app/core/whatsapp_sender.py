"""Envío de mensajes de texto vía WhatsApp Cloud API."""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_WA_API_BASE = "https://graph.facebook.com/v20.0"
_TIMEOUT = 10.0  # segundos


async def send_whatsapp_message(phone_number_id: str, to_wa_id: str, text: str) -> None:
    """
    Envía un mensaje de texto al usuario vía WhatsApp Cloud API.

    Args:
        phone_number_id: ID del número de WhatsApp Business (el nuestro).
        to_wa_id: Número de WhatsApp del destinatario (ej: "5491112345678").
        text: Texto a enviar.
    """
    url = f"{_WA_API_BASE}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_wa_id,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.is_success:
        data = response.json()
        wamid = data.get("messages", [{}])[0].get("id", "unknown")
        logger.info("Mensaje enviado a %s — wamid=%s", to_wa_id, wamid)
    else:
        logger.error(
            "Error al enviar mensaje a %s: HTTP %d — %s",
            to_wa_id,
            response.status_code,
            response.text,
        )
        response.raise_for_status()
