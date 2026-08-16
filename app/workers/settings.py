"""WorkerSettings unificado: registra todos los workers ARQ del proyecto.

Usar como punto de entrada del proceso ARQ:
    arq app.workers.settings.WorkerSettings

Agregar nuevos workers aquí — no en cada archivo individual.
"""
from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.instagram import process_instagram_message
from app.workers.whatsapp import process_whatsapp_message


class WorkerSettings:
    functions = [
        process_whatsapp_message,
        process_instagram_message,
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs: int = 10
    job_timeout: int = 300
    retry_jobs: bool = True
    max_tries: int = 3
    health_check_interval: int = 30
