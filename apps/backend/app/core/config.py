"""Typed configuration. All values come from environment (12-factor); no secrets in code."""

from __future__ import annotations

import os
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4] if len(Path(__file__).resolve().parents) > 4 else Path("/app")
# In containers the contracts package is copied to /contracts (see apps/backend/Dockerfile).
CONTRACTS_DIR = Path(os.environ.get("COS_CONTRACTS_DIR", REPO_ROOT / "packages" / "contracts"))


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="COS_", extra="ignore")

    environment: Environment = Environment.DEVELOPMENT
    service_name: str = "commerce-os-api"
    log_level: str = "INFO"
    log_json: bool = True

    database_url: str = "postgresql+psycopg://localhost:5432/commerce_os"
    database_pool_size: int = 10
    database_max_overflow: int = 10
    database_statement_timeout_ms: int = 15_000
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None

    # Auth
    jwt_secret: SecretStr = SecretStr("dev-only-change-me-dev-only-change-me")
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "commerce-os"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 30
    mfa_token_ttl_seconds: int = 300
    login_max_failures: int = 10
    login_lockout_seconds: int = 900
    staff_require_mfa: bool = True

    # Envelope encryption key-encryption-key (base64, 32 bytes). Production must use KMS provider.
    kek_provider: str = "local"
    local_kek_b64: SecretStr = SecretStr("ZGV2LW9ubHkta2VrLWRldi1vbmx5LWtlay0zMmJ5dGU=")

    # CORS / web
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    trusted_proxy_count: int = 0

    # Object storage
    storage_backend: str = "local"  # local | s3
    storage_local_root: Path = REPO_ROOT / ".data" / "objects"
    s3_endpoint_url: str | None = None
    s3_bucket: str = "commerce-os-private"
    s3_region: str = "us-east-1"
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None

    # Media
    media_max_upload_bytes: int = 20 * 1024 * 1024
    media_upload_ttl_seconds: int = 900
    malware_scanner: str = "none"  # none (dev/test only) | clamd
    clamd_host: str = "localhost"
    clamd_port: int = 3310
    public_api_base_url: str = "http://localhost:8000"

    # Channels: per-provider webhook signing secrets (app-level, from the secret manager in prod)
    channel_webhook_secrets: dict[str, SecretStr] = Field(
        default_factory=lambda: {"sandbox_channel": SecretStr("dev-sandbox-webhook-secret")}
    )
    webhook_max_bytes: int = 1024 * 1024

    # AI provider platform keys (server-side only; never sent to clients or logged)
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    ai_routing_policy_path: Path = CONTRACTS_DIR / "ai-routing-policy.example.json"
    ai_enable_sandbox_provider: bool = True

    # Observability
    otel_exporter_otlp_endpoint: str | None = None
    metrics_enabled: bool = True

    # Outbox
    outbox_batch_size: int = 100
    outbox_max_attempts: int = 12

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        if self.environment in (Environment.STAGING, Environment.PRODUCTION):
            if (
                "dev-only" in self.jwt_secret.get_secret_value()
                or len(self.jwt_secret.get_secret_value()) < 32
            ):
                raise ValueError("COS_JWT_SECRET must be a strong secret outside development")
            if self.kek_provider == "local" and self.environment == Environment.PRODUCTION:
                raise ValueError("Production requires a KMS key provider (COS_KEK_PROVIDER)")
            if "ZGV2LW9ubHkta2Vr" in self.local_kek_b64.get_secret_value():
                raise ValueError("COS_LOCAL_KEK_B64 must not use the development key outside development")
            if self.ai_enable_sandbox_provider and self.environment == Environment.PRODUCTION:
                raise ValueError("Sandbox AI provider must be disabled in production")
            if self.malware_scanner == "none" and self.environment == Environment.PRODUCTION:
                raise ValueError(
                    "Production requires a malware scanner for uploads (COS_MALWARE_SCANNER=clamd)"
                )
        return self

    @property
    def is_production_like(self) -> bool:
        return self.environment in (Environment.STAGING, Environment.PRODUCTION)

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
