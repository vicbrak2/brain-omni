from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # WhatsApp Cloud API
    whatsapp_verify_token: str = "dev_verify_token"
    whatsapp_app_secret: str = ""
    whatsapp_api_token: str = ""
    whatsapp_phone_id: str = ""

    # Instagram / Messenger API para DMs
    # INSTAGRAM_ACCESS_TOKEN: token de larga duración con instagram_manage_messages
    # INSTAGRAM_APP_SECRET: para validar firma del webhook (X-Hub-Signature-256)
    # INSTAGRAM_VERIFY_TOKEN: token de verificación del webhook en Meta Business
    instagram_access_token: str = ""
    instagram_app_secret: str = ""
    instagram_verify_token: str = "dev_ig_verify_token"

    # LLM Providers (Brain chain: openrouter → cerebras → hf → groq)
    openrouter_api_key: str = ""
    cerebras_api_key: str = ""
    hf_token: str = ""
    groq_api_key: str = ""

    # Redis / ARQ
    redis_url: str = "redis://localhost:6379"

    # PostgreSQL (asyncpg: postgresql://user:pass@host:port/db)
    # Railway genera DATABASE_URL automáticamente al agregar el plugin
    database_url: str = "postgresql://localhost/brain_omni"

    # App
    debug: bool = False

    # Panel de administración (GET /panel)
    # Genera con: openssl rand -hex 32
    admin_api_token: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
