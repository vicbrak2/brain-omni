from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # WhatsApp Cloud API
    whatsapp_verify_token: str = "dev_verify_token"
    whatsapp_app_secret: str = ""
    whatsapp_api_token: str = ""
    whatsapp_phone_id: str = ""

    # Redis / ARQ
    redis_url: str = "redis://localhost:6379"

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://localhost/brain_omni"

    # App
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
