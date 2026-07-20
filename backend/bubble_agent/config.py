from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="BUBBLE_AGENT_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "Bubble Agent"
    app_version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: Path = Field(default_factory=lambda: Path.cwd() / "data")
    api_token: str | None = None
    default_provider: str = "demo"
    default_model: str = "bubble-demo-v1"
    model_base_url: str | None = None
    model_api_key: str | None = None
    request_timeout_seconds: float = 60.0

    @property
    def database_url(self) -> str:
        return f"sqlite:///{(self.data_dir / 'bubble-agent.db').as_posix()}"

    @property
    def checkpoint_path(self) -> Path:
        return self.data_dir / "langgraph-checkpoints.db"

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
