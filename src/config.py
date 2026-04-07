"""Environment-based application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    """Raised when mandatory runtime configuration is missing."""


@dataclass(slots=True)
class AppConfig:
    model_name: str
    embedding_model: str
    database_url: str
    vector_db_provider: str
    openai_api_key: str | None
    anthropic_api_key: str | None
    google_api_key: str | None


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ConfigError(f"Missing required environment variable: {name}")
    return value.strip()


def _load_dotenv_if_present() -> None:
    """Load .env from repository root into process env."""

    dotenv_path = Path(__file__).resolve().parents[1] / ".env"
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key.startswith("export "):
            key = key.replace("export ", "", 1).strip()
        if not key:
            continue
        if (
            len(value) >= 2
            and ((value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")))
        ):
            value = value[1:-1]
        # Do not override shell-provided variables.
        os.environ.setdefault(key, value)


def load_config() -> AppConfig:
    """Load runtime settings from environment variables."""

    _load_dotenv_if_present()

    return AppConfig(
        model_name=os.getenv("MODEL_NAME", "gpt-4.1-mini"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        database_url=_required_env("DATABASE_URL"),
        vector_db_provider=os.getenv("VECTOR_DB_PROVIDER", "chroma"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
