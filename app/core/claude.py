"""Cliente Claude (Anthropic) para generar respuestas conversacionales."""
from __future__ import annotations

import logging
from typing import Any

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

# Modelo rápido y económico, ideal para WhatsApp
_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = (
    "Eres un asistente de atención al cliente amable y conciso. "
    "Responde siempre en el mismo idioma que usa el usuario. "
    "Mantén las respuestas breves (máximo 3 párrafos cortos) "
    "para que sean fáciles de leer en WhatsApp."
)


async def call_claude(history: list[dict[str, Any]]) -> str:
    """
    Llama a la API de Claude con el historial de la conversación.

    Args:
        history: Lista de dicts con claves 'role' y 'content'.
                 Roles válidos: 'user', 'assistant'.

    Returns:
        Texto de la respuesta generada por Claude.
    """
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY no está configurada — "
            "añádela como variable de entorno."
        )

    messages = [
        {"role": row["role"], "content": row["content"]}
        for row in history
        if row["role"] in ("user", "assistant")
    ]

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=messages,
    )

    text = response.content[0].text
    logger.debug(
        "Claude respondió con %d tokens de entrada y %d de salida",
        response.usage.input_tokens,
        response.usage.output_tokens,
    )
    return text
