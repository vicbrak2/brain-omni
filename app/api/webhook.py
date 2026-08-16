"""Webhook ingress para WhatsApp e Instagram (Messenger Platform).

Flujo (ambos canales):
  GET  /webhook/{canal}  →  handshake de verificación Meta
  POST /webhook/{canal}  →  validar firma → encolar en ARQ → 200 OK inmediato

IMPORTANTE: Meta reintenta durante 7 días si no recibe 200 en < 10 s.
Por eso la lógica de negocio va en los workers ARQ, nunca aquí.
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


# ── WhatsApp ──────────────────────────────────────────────────────────────────

@router.get("/whatsapp", response_class=PlainTextResponse)
async def verify_whatsapp_webhook(request: Request) -> str:
    """Handshake de verificación Meta para WhatsApp."""
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


@router.post("/whatsapp", status_code=status.HTTP_200_OK)
async def receive_whatsapp_webhook(request: Request) -> dict:
    """Recibe eventos de WhatsApp, valida la firma y encola para procesamiento."""
    raw_body = await request.body()
    _verify_signature(raw_body, request.headers.get("X-Hub-Signature-256", ""),
                      settings.whatsapp_app_secret, "WHATSAPP_APP_SECRET")

    try:
        payload: dict = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload inválido")

    if not payload.get("entry"):
        return {"status": "ignored"}

    try:
        redis = await arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.redis_url))
        await redis.enqueue_job("process_whatsapp_message", payload)
        await redis.aclose()
    except Exception as exc:
        logger.error("Error al encolar mensaje WhatsApp: %s", exc, exc_info=True)

    return {"status": "queued"}


# ── Instagram ─────────────────────────────────────────────────────────────────

@router.get("/instagram", response_class=PlainTextResponse)
async def verify_instagram_webhook(request: Request) -> str:
    """Handshake de verificación Meta para Instagram Messaging."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and token == settings.instagram_verify_token:
        logger.info("Webhook Instagram verificado correctamente")
        return challenge

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Token de verificación inválido",
    )


@router.post("/instagram", status_code=status.HTTP_200_OK)
async def receive_instagram_webhook(request: Request) -> dict:
    """
    Recibe eventos de Instagram Messaging (DMs), valida la firma y encola.

    Meta envía el mismo payload tanto para mensajes entrantes como para
    notificaciones de entrega/lectura — el worker filtra por tipo.
    """
    raw_body = await request.body()
    _verify_signature(raw_body, request.headers.get("X-Hub-Signature-256", ""),
                      settings.instagram_app_secret, "INSTAGRAM_APP_SECRET")

    try:
        payload: dict = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload inválido")

    # Ignorar payloads sin entry o sin eventos messaging
    entry = payload.get("entry", [])
    if not entry or not entry[0].get("messaging"):
        return {"status": "ignored"}

    try:
        redis = await arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.redis_url))
        await redis.enqueue_job("process_instagram_message", payload)
        await redis.aclose()
    except Exception as exc:
        logger.error("Error al encolar DM de Instagram: %s", exc, exc_info=True)

    return {"status": "queued"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verify_signature(
    raw_body: bytes,
    signature_header: str,
    app_secret: str,
    secret_env_name: str,
) -> None:
    """Valida la firma HMAC-SHA256 de Meta. Lanza HTTPException 401 si es inválida."""
    if not app_secret:
        logger.warning("%s no configurado — firma no validada", secret_env_name)
        return

    if not signature_header.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabecera X-Hub-Signature-256 ausente o malformada",
        )

    received_sig = signature_header[len("sha256="):]
    expected_sig = hmac.new(
        app_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(received_sig, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firma HMAC inválida",
        )
