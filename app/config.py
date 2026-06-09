from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    app_env: str = "development"
    secret_key: str = "change_me_in_production_minimum_32_chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    database_url: str = "postgresql+asyncpg://fraudvault:password@localhost:5432/fraudvault"
    database_sync_url: str = "postgresql://fraudvault:password@localhost:5432/fraudvault"

    redis_url: str = "redis://localhost:6379/0"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_meter_event_name: str = "fraudvault_detection_hit"

    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "fraudvault-files"
    r2_public_url: str = "https://files.fraudvault.io"
    r2_endpoint_url: str = ""

    local_storage_dir: str = "./storage"
    model_cache_dir: str = "./models"
    huggingface_hub_token: str = ""

    internal_service_key: str = "change_me"
    max_file_size_mb: int = 50

    ai_generated_threshold: float = 0.40
    ai_inconclusive_threshold: float = 0.30
    forensic_tampered_threshold: float = 0.75
    forensic_inconclusive_threshold: float = 0.55
    forensic_elevated_threshold: float = 0.45

    @property
    def use_local_storage(self) -> bool:
        return not self.r2_access_key_id or self.app_env == "development"

    @property
    def r2_endpoint(self) -> str:
        if self.r2_endpoint_url:
            return self.r2_endpoint_url
        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
