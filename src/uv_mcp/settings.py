"""Server configuration loaded from environment variables."""

import logging
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server settings, configurable via ``UV_MCP_*`` environment variables."""

    model_config = SettingsConfigDict(env_prefix="UV_MCP_")

    venv_path: str | None = None
    log_level: str = "INFO"
    uv_binary: str | None = None
    command_timeout: float | None = None
    cache_dir: str | None = None


def configure_logging(settings: Settings) -> None:
    """Configure stdio-safe logging on stderr for the given settings."""
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(levelname)s:%(name)s:%(message)s",
        stream=sys.stderr,
    )
