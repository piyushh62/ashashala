from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Required: LLM Providers ---
    GEMINI_API_KEY: str = Field(..., description="Google AI Studio API key")
    NVIDIA_API_KEY: str = Field(..., description="NVIDIA NGC API key")
    NVIDIA_BASE_URL: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="NVIDIA NIM base URL",
    )

    # --- Required: Database ---
    DATABASE_URL: str = Field(..., description="Neon Postgres connection string")

    # --- Required: Vector DB ---
    QDRANT_URL: str = Field(..., description="Qdrant Cloud cluster URL")
    QDRANT_API_KEY: str = Field(..., description="Qdrant Cloud API key")

    # --- Required: Object Storage ---
    R2_ACCOUNT_ID: str = Field(..., description="Cloudflare R2 account ID")
    R2_ACCESS_KEY_ID: str = Field(..., description="Cloudflare R2 access key ID")
    R2_SECRET_ACCESS_KEY: str = Field(..., description="Cloudflare R2 secret access key")
    R2_BUCKET_NAME: str = Field(..., description="Cloudflare R2 bucket name")
    R2_PUBLIC_URL: str = Field(..., description="Cloudflare R2 public URL base")

    # --- Required: Auth ---
    JWT_SECRET: str = Field(..., description="JWT access token secret (64 chars)")
    JWT_REFRESH_SECRET: str = Field(..., description="JWT refresh token secret (64 chars)")
    SUPER_ADMIN_EMAIL: str = Field(..., description="Super admin email for seeding")
    SUPER_ADMIN_PASSWORD: str = Field(..., description="Super admin password for seeding")

    # --- Required: CORS ---
    ALLOWED_ORIGINS: str = Field(..., description="Comma-separated CORS origins")

    # --- Optional: Observability ---
    SENTRY_DSN: str | None = Field(default=None, description="Sentry DSN for error tracking")

    # --- App metadata ---
    APP_VERSION: str = Field(default="0.1.0", description="API version string")
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = Field(
        default="development", description="Runtime environment"
    )

    # --- Optional: Development ---
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    MOCK_EXTERNAL_SERVICES: bool = Field(
        default=False,
        description="When true, external clients short-circuit health checks (tests/CI)",
    )

    # --- Timeouts (seconds) ---
    GEMINI_TIMEOUT: int = Field(default=30, description="Gemini API timeout")
    NVIDIA_TIMEOUT: int = Field(default=45, description="NVIDIA API timeout")
    QDRANT_TIMEOUT: int = Field(default=10, description="Qdrant query timeout")
    R2_TIMEOUT: int = Field(default=60, description="R2 upload timeout")

    @field_validator("JWT_SECRET", "JWT_REFRESH_SECRET")
    @classmethod
    def validate_jwt_secrets(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT secrets must be at least 32 characters")
        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse the comma-separated ALLOWED_ORIGINS string into a list."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()