"""Webhook ingress para WhatsApp Cloud API.

Flujo:
  GET  /webhook/whatsapp  →  handshake de verificación Meta
  POST /webhook/whatsapp  →  validar firma → encolar en ARQ → 200 OK inmediato

IMPORTANTE: Meta reintenta durante 7 días si no recibe 200 en < 10 s.
Por eso la lógica de negocio va en el worker ARQ, nunca aquí.
"""
import hashlib
import hmac
import json
import logging

import arq
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import PlainTextResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])


# ---------------------------------------------------------------------------
# GET  /webhook/whatsapp
# Meta llama a este endpoint al configurar el webhook en el panel de Meta.
# ---------------------------------------------------------------------------
@router.get("/whatsapp", response_class=PlainTextResponse)
async def verify_webhook(request: Request) -> str:
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("Webhook WhatsApp verificado correctamente")
        return challenge

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Token de verificación inválido",
    )


# ---------------------------------------------------------------------------
# POST /webhook/whatsapp
# ---------------------------------------------------------------------------
@router.post("/whatsapp", status_code=status.HTTP_200_OK)
async def receive_webhook(request: Request) -> dict:
    """Recibe eventos de WhatsApp, valida la firma y encola para procesamiento."""
    raw_body = await request.body()

    # 1. Validar firma X-Hub-Signature-256
    _verify_signature(raw_body, request.headers.get("X-Hub-Signature-256", ""))

    # 2. Parsear payload
    try:
        payload: dict = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload inválido",
        )

    # 3. Ignorar eventos que no son mensajes de texto (ej: status de entrega)
    entry = payload.get("entry", [])
    if not entry:
        return {"status": "ignored"}

    # 4. Encolar en ARQ (Redis) — regresa 200 en < 1 ms
    try:
        redis = await arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.redis_url))
        await redis.enqueue_job("process_whatsapp_message", payload)
        await redis.aclose()
    except Exception as exc:
        # Log pero nunca fallar — Meta reintentaría innecesariamente
        logger.error("Error al encolar mensaje WhatsApp: %s", exc, exc_info=True)

    return {"status": "queued"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _verify_signature(raw_body: bytes, signature_header: str) -> None:
    """Lanza HTTPException 401 si la firma HMAC-SHA256 no coincide."""
    if not settings.whatsapp_app_secret:
        # En desarrollo sin secret configurado, omitir validación
        logger.warning("WHATSAPP_APP_SECRET no configurado — firma no validada")
        return

    if not signature_header.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabecera X-Hub-Signature-256 ausente o malformada",
        )

    received_sig = signature_header[len("sha256="):]
    expected_sig = hmac.new(
        settings.whatsapp_app_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(received_sig, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firma HMAC inválida",
        )
