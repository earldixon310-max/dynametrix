"""
Centralized configuration.

All secrets and environment-dependent values are loaded here. Never hardcode
secrets anywhere else in the codebase.
"""
from functools import lru_cache
from typing import List

from pydantic import Field, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "Dynametrix"
    APP_ENV: str = "development"   # development | staging | production
    APP_DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # CORS — comma-separated list of origins
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- Auth ---
    JWT_SECRET: str = Field(..., description="HMAC secret for signing JWTs")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRES_MIN: int = 30
    REFRESH_TOKEN_EXPIRES_DAYS: int = 14

    # --- Database ---
    DATABASE_URL: str = Field(..., description="PostgreSQL DSN, e.g. postgresql+psycopg://...")

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --- Stripe ---
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_TRIAL: str = ""
    STRIPE_PRICE_SINGLE: str = ""
    STRIPE_PRICE_MULTI: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""
    STRIPE_PORTAL_RETURN_URL: str = "http://localhost:3000/billing"
    STRIPE_CHECKOUT_SUCCESS_URL: str = "http://localhost:3000/billing/success"
    STRIPE_CHECKOUT_CANCEL_URL: str = "http://localhost:3000/billing/cancel"

    # --- Email (alerts) ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "alerts@dynametrix.io"

    # --- Object storage (reports) ---
    REPORTS_BUCKET: str = "dynametrix-reports"
    REPORTS_LOCAL_DIR: str = "/var/dynametrix/reports"   # used when AWS not configured
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # --- Engine ---
    ENGINE_TOOLS_DIR: str = "/app/tools"
    DEFAULT_MODEL_VERSION: str = "calibrator-v1.0"
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.65
    ALERT_COOLDOWN_MINUTES: int = 30

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
