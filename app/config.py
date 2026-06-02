from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./opspilot.db"
    llm_provider: str = "fake"
    openai_base_url: str = ""
    openai_api_key: str = ""
    model: str = ""
    inbox_path: str = "examples/inbox"
    execution_mode: Literal["dry_run", "webhook"] = "dry_run"
    webhook_sink_url: str = ""
    webhook_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(env_prefix="OPSPILOT_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
