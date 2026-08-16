"""LLM call: capa fina sobre Brain que mantiene la misma interfaz del worker.

La cadena de providers refleja la de llm-virtual-brain (DEFAULT_PROVIDERS):
  openrouter → cerebras → hf → groq

Cada provider entra a la cadena solo si su API key está definida en el entorno.
Si todos fallan, Brain lanza BrainError con el detalle de cada error.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from .brain import Brain, BrainError
from .providers import provider_from_dict

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Eres un asistente de atención al cliente amable y conciso. "
    "Responde siempre en el mismo idioma que usa el usuario. "
    "Mantén las respuestas breves (máximo 3 párrafos cortos) "
    "para que sean fáciles de leer en WhatsApp o Instagram."
)

# Cadena de providers — mismo orden que llm-virtual-brain/brain/config.py
_PROVIDER_CHAIN = [
    {
        "name": "openrouter",
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "model": "mistralai/mistral-small-3.2-24b-instruct",
    },
    {
        "name": "cerebras",
        "api_key": os.getenv("CEREBRAS_API_KEY", ""),
        "model": "gemma-4-31b",
        "extra_body": {"reasoning_effort": "high"},
    },
    {
        "name": "hf",
        "api_key": os.getenv("HF_TOKEN", ""),
    },
    {
        "name": "groq",
        "api_key": os.getenv("GROQ_API_KEY", ""),
        "model": "openai/gpt-oss-120b",
    },
]


def _build_brain() -> Brain:
    """Construye el Brain con los providers configurados en el entorno."""
    providers = [provider_from_dict(p) for p in _PROVIDER_CHAIN]
    return Brain(providers=providers, app_name="brain-omni", timeout_seconds=30)


async def call_claude(
    history: list[dict[str, Any]],
    system_prompt: str | None = None,
) -> str:
    """
    Llama al LLM con el historial de la conversación.

    Args:
        history:       Lista de dicts con claves 'role' y 'content'.
                       Roles válidos: 'user', 'assistant'.
        system_prompt: Prompt del sistema específico del tenant (de agent_config).
                       Si es None o vacío, se usa el prompt genérico por defecto.

    Returns:
        Texto de la respuesta generada.

    Raises:
        BrainError: Si todos los providers fallan.
    """
    system = (system_prompt.strip() if system_prompt and system_prompt.strip()
              else _SYSTEM_PROMPT)

    messages = [
        {"role": "system", "content": system},
        *[
            {"role": row["role"], "content": row["content"]}
            for row in history
            if row["role"] in ("user", "assistant")
        ],
    ]

    brain = _build_brain()
    text = await brain.complete(messages, max_tokens=800, temperature=0.3)
    provider = brain._last_used or "unknown"
    logger.info("Brain respondió via %s (%d msgs, prompt=%s)",
                provider, len(history), "custom" if system_prompt else "default")
    return text
