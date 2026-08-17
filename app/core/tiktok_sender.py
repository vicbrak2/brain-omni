"""Respuesta a comentarios de TikTok vía TikTok for Business API.

TikTok no tiene un canal de mensajería directa accesible por API para
la mayoría de las cuentas. El flujo más común para moderación automática
es responder a comentarios en videos.

Referencia: https://developers.tiktok.com/doc/comment-api
Endpoint v2: POST /v2/comment/reply/

IMPORTANTE: El Comment Reply API requiere:
  - Acceso a TikTok for Business Developer (aprobación de app)
  - Permisos: comment.list, video.list, research.adlib.basic
  - Token de acceso del Content Posting API o Research API
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"
_TIMEOUT = 10.0


async def reply_tiktok_comment(
    video_id: str,
    comment_id: str,
    text: str,
) -> None:
    """
    Publica una respuesta a un comentario de TikTok.

    Args:
        video_id: ID del video donde se publicó el comentario original.
        comment_id: ID del comentario al que se responde.
        text: Texto de la respuesta (máx. 150 caracteres en TikTok).

    Requiere:
        TIKTOK_ACCESS_TOKEN con permisos de Comment Reply API.
    """
    url = f"{_TIKTOK_API_BASE}/comment/reply/"
    headers = {
        "Authorization": f"Bearer {settings.tiktok_access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    # TikTok trunca comentarios a 150 chars
    reply_text = text[:150]

    payload = {
        "video_id":   video_id,
        "comment_id": comment_id,
        "text":       reply_text,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.is_success:
        data = response.json()
        reply_id = data.get("data", {}).get("id", "unknown")
        logger.info(
            "TikTok reply publicado en comentario %s — reply_id=%s",
            comment_id, reply_id,
        )
    else:
        logger.error(
            "Error al responder TikTok comentario %s: HTTP %d — %s",
            comment_id,
            response.status_code,
            response.text,
        )
        response.raise_for_status()
