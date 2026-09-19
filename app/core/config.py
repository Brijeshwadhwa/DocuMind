import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "DocuMind"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Security & Authentication
    SECRET_KEY: str = "dev_secret_key_antigravity_document_intelligence_service_2026_secure!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database
    DATABASE_URL: str = "sqlite:///./document_intelligence.db"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = True

    # Storage & Upload limits
    UPLOAD_DIR: str = "./storage/uploads"
    MAX_FILE_SIZE_MB: int = 15
    ALLOWED_EXTENSIONS: str = "pdf,png,jpg,jpeg"

    # OCR Settings
    TESSERACT_CMD: str = "tesseract"
    OCR_FALLBACK_ENABLED: bool = True
    OCR_DPI: int = 300

    # Optional External AI/OCR Service
    EXTERNAL_AI_ENABLED: bool = False
    EXTERNAL_AI_PROVIDER: str = "none"
    EXTERNAL_AI_API_KEY: str = ""

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",") if ext.strip()]


settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
