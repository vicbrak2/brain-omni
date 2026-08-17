"""WorkerSettings unificado: registra todos los workers ARQ del proyecto.

Usar como punto de entrada del proceso ARQ:
    arq app.workers.settings.WorkerSettings

Agregar nuevos workers aquí — no en cada archivo individual.

Workers registrados:
  Scope EXTERNAL (interacción pública):
    - process_whatsapp_message   → WhatsApp Business API
    - process_instagram_message  → Instagram DMs
    - process_facebook_message   → Facebook Messenger
    - process_tiktok_comment     → TikTok comentarios (scope externo)
"""
from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.facebook import process_facebook_message
from app.workers.instagram import process_instagram_message
from app.workers.tiktok import process_tiktok_comment
from app.workers.whatsapp import process_whatsapp_message


class WorkerSettings:
    functions = [
        # ── Scope EXTERNAL ────────────────────────────────────────────────────
        process_whatsapp_message,    # WA-Ext
        process_instagram_message,   # IG-Ext
        process_facebook_message,    # FB-Ext
        process_tiktok_comment,      # TT-Ext
        # ── Scope INTERNAL ────────────────────────────────────────────────────
        # Los agentes internos (IG-Int, FB-Int, TT-Int) se invocan desde el
        # panel de administración vía API endpoints — no tienen worker ARQ propio
        # porque son on-demand, no reactivos a webhooks entrantes.
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs: int = 10
    job_timeout: int = 300
    retry_jobs: bool = True
    max_tries: int = 3
    health_check_interval: int = 30
