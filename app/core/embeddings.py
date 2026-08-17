"""Generación de embeddings y chunking de texto.

Modelo: paraphrase-multilingual-MiniLM-L12-v2
- Gratis via HuggingFace Inference API
- 384 dimensiones
- Soporta español nativamente
- Límite: 512 tokens por chunk (~300 palabras)
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_HF_MODEL   = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_HF_URL     = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{_HF_MODEL}"
_CHUNK_WORDS = 200    # palabras por chunk (≈ 280 tokens)
_OVERLAP     = 20     # palabras de solapamiento entre chunks


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str) -> list[str]:
    """Divide el texto en chunks de tamaño fijo con solapamiento."""
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + _CHUNK_WORDS])
        chunks.append(chunk)
        i += _CHUNK_WORDS - _OVERLAP
    return chunks


# ── Embedding ─────────────────────────────────────────────────────────────────

async def embed(text: str) -> list[float] | None:
    """Genera embedding para un texto. Retorna None si hay error."""
    if not settings.hf_token:
        logger.warning("HF_TOKEN no configurado — RAG desactivado")
        return None

    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(
                _HF_URL,
                json={"inputs": text, "options": {"wait_for_model": True}},
                headers={"Authorization": f"Bearer {settings.hf_token}"},
            )
            r.raise_for_status()

        result = r.json()

        # El pipeline de HF retorna distintas formas según el modelo:
        # [[e1, e2, ...]] para sentence-transformers (lista de listas)
        # [e1, e2, ...] para otros modelos
        if result and isinstance(result[0], list):
            return result[0]
        return result  # type: ignore[return-value]

    except Exception as exc:  # noqa: BLE001
        logger.warning("Error generando embedding: %s", exc)
        return None


async def embed_chunks(chunks: list[str]) -> list[list[float] | None]:
    """Embeds cada chunk — llamadas individuales para no exceder el payload."""
    results = []
    for chunk in chunks:
        emb = await embed(chunk)
        results.append(emb)
    return results


def vec_to_str(embedding: list[float]) -> str:
    """Formatea embedding como string para pgvector: [0.1,0.2,...]"""
    return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"
