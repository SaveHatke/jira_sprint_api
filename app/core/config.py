from __future__ import annotations

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    jira_base_url: AnyHttpUrl = Field(..., alias="JIRA_BASE_URL")
    jira_pat: str = Field(..., alias="JIRA_PAT")
    jira_auth_scheme: str = Field("bearer", alias="JIRA_AUTH_SCHEME")  # bearer|basic
    jira_username: str | None = Field(None, alias="JIRA_USERNAME")

    jira_board_id: int = Field(..., alias="JIRA_BOARD_ID")

    http_timeout_seconds: float = Field(20.0, alias="HTTP_TIMEOUT_SECONDS")
    http_max_retries: int = Field(4, alias="HTTP_MAX_RETRIES")
    http_backoff_min_seconds: float = Field(0.5, alias="HTTP_BACKOFF_MIN_SECONDS")
    http_backoff_max_seconds: float = Field(6.0, alias="HTTP_BACKOFF_MAX_SECONDS")

    cache_enabled: bool = Field(True, alias="CACHE_ENABLED")
    cache_ttl_seconds: int = Field(60, alias="CACHE_TTL_SECONDS")
    cache_maxsize: int = Field(256, alias="CACHE_MAXSIZE")

    log_level: str = Field("INFO", alias="LOG_LEVEL")


settings = Settings()
