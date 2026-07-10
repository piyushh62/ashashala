from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
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
    # Cloudflare R2 can still be used via R2_* variables.
    # Generic S3-compatible storage can use STORAGE_* variables.
    R2_ACCOUNT_ID: str | None = Field(
        default=None,
        description="Cloudflare R2 account ID",
    )
    R2_ACCESS_KEY_ID: str | None = Field(
        default=None,
        description="Cloudflare R2 access key ID",
    )
    R2_SECRET_ACCESS_KEY: str | None = Field(
        default=None,
        description="Cloudflare R2 secret access key",
    )
    R2_BUCKET_NAME: str | None = Field(
        default=None,
        description="Cloudflare R2 bucket name",
    )
    R2_PUBLIC_URL: str | None = Field(
        default=None,
        description="Cloudflare R2 public URL base",
    )

    STORAGE_ENDPOINT_URL: str | None = Field(
        default=None,
        description="S3-compatible object storage endpoint URL",
    )
    STORAGE_ACCESS_KEY_ID: str | None = Field(
        default=None,
        description="S3-compatible object storage access key ID",
    )
    STORAGE_SECRET_ACCESS_KEY: str | None = Field(
        default=None,
        description="S3-compatible object storage secret access key",
    )
    STORAGE_BUCKET_NAME: str | None = Field(
        default=None,
        description="S3-compatible object storage bucket name",
    )
    STORAGE_PUBLIC_URL: str | None = Field(
        default=None,
        description="S3-compatible object storage public URL base",
    )
    STORAGE_REGION: str = Field(
        default="auto",
        description="S3-compatible object storage region",
    )

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

    # --- Rate limits (slowapi syntax, e.g. "30/minute") ---
    CHAT_RATE_LIMIT: str = Field(default="30/minute", description="Per-IP limit on the chat endpoint")
    QUIZ_RATE_LIMIT: str = Field(default="20/minute", description="Per-IP limit on quiz generation")
    LOGIN_RATE_LIMIT: str = Field(
        default="10/minute", description="Per-IP limit on login/refresh/password-reset"
    )

    # --- Safety ---
    ENABLE_JAILBREAK_DETECTION: bool = Field(
        default=False,
        description="Run the NVIDIA NeMo-Guard jailbreak classifier per chat message "
        "(spends an embedding + classifier call on the rate-limited free tier).",
    )

    # --- Timeouts (seconds) ---
    GEMINI_TIMEOUT: int = Field(default=30, description="Gemini API timeout")
    NVIDIA_TIMEOUT: int = Field(default=45, description="NVIDIA API timeout")
    QDRANT_TIMEOUT: int = Field(default=10, description="Qdrant query timeout")
    R2_TIMEOUT: int = Field(default=60, description="R2 upload timeout")

    # --- Optional: SMS/WhatsApp providers ---
    # Unused today — every channel is served by the log-only LogSender stub
    # (see app/services/notification_dispatch.py). Shaped for a future real
    # provider to drop in without further config changes.
    TWILIO_ACCOUNT_SID: str | None = Field(default=None, description="Twilio account SID (SMS)")
    TWILIO_AUTH_TOKEN: str | None = Field(default=None, description="Twilio auth token (SMS)")
    TWILIO_FROM_NUMBER: str | None = Field(default=None, description="Twilio sending number (SMS)")
    WHATSAPP_BUSINESS_TOKEN: str | None = Field(default=None, description="WhatsApp Business API token")
    WHATSAPP_PHONE_NUMBER_ID: str | None = Field(default=None, description="WhatsApp Business phone number id")
    NOTIFICATION_DISPATCH_INTERVAL_SECONDS: int = Field(
        default=60, description="APScheduler poll interval for pending sms/whatsapp notifications"
    )

    # --- Phase 3: proactive agents (Scheduling, Insight, Scheduled-Learning) ---
    SCHEDULING_MAX_PERIODS_PER_DAY: int = Field(
        default=8, description="Highest period_number the Scheduling Agent's free-slot grid considers"
    )
    INSIGHT_STRUGGLE_THRESHOLD: int = Field(
        default=40, description="mastery_score below this triggers an Insight Agent alert"
    )
    INSIGHT_REALERT_COOLDOWN_DAYS: int = Field(
        default=7, description="Days to suppress a repeat Insight alert for the same student+topic"
    )
    INSIGHT_SCAN_CRON_HOUR: int = Field(
        default=2, description="Local hour (0-23) the nightly Insight Agent scan runs"
    )
    SCHEDULED_LEARNING_CRON_HOUR: int = Field(
        default=5, description="Local hour (0-23) the daily Scheduled-Learning feed generation runs"
    )

    @model_validator(mode="after")
    def validate_storage_config(self):
        r2_enabled = all(
            [
                self.R2_ACCOUNT_ID,
                self.R2_ACCESS_KEY_ID,
                self.R2_SECRET_ACCESS_KEY,
                self.R2_BUCKET_NAME,
                self.R2_PUBLIC_URL,
            ]
        )
        storage_enabled = all(
            [
                self.STORAGE_ENDPOINT_URL,
                self.STORAGE_ACCESS_KEY_ID,
                self.STORAGE_SECRET_ACCESS_KEY,
                self.STORAGE_BUCKET_NAME,
                self.STORAGE_PUBLIC_URL,
            ]
        )
        if not (r2_enabled or storage_enabled):
            raise ValueError(
                "Either R2_* or STORAGE_* object storage credentials must be configured."
            )
        return self

    @property
    def storage_endpoint_url(self) -> str:
        if self.STORAGE_ENDPOINT_URL:
            return self.STORAGE_ENDPOINT_URL
        if self.R2_ACCOUNT_ID:
            return f"https://{self.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        raise ValueError("No object storage endpoint configured")

    @property
    def storage_access_key_id(self) -> str:
        return self.STORAGE_ACCESS_KEY_ID or self.R2_ACCESS_KEY_ID  # type: ignore[return-value]

    @property
    def storage_secret_access_key(self) -> str:
        return self.STORAGE_SECRET_ACCESS_KEY or self.R2_SECRET_ACCESS_KEY  # type: ignore[return-value]

    @property
    def storage_bucket_name(self) -> str:
        return self.STORAGE_BUCKET_NAME or self.R2_BUCKET_NAME  # type: ignore[return-value]

    @property
    def storage_public_url(self) -> str:
        return self.STORAGE_PUBLIC_URL or self.R2_PUBLIC_URL  # type: ignore[return-value]

    @property
    def storage_region(self) -> str:
        return self.STORAGE_REGION

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
