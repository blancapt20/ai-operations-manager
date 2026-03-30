"""Environment-based application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class AppConfig:
    model_name: str
    embedding_model: str
    database_url: str
    vector_db_provider: str
    openai_api_key: str | None
    anthropic_api_key: str | None
    google_api_key: str | None


def load_config() -> AppConfig:
    """Load runtime settings from environment variables with safe defaults."""

    return AppConfig(
        model_name=os.getenv("MODEL_NAME", "gpt-4.1-mini"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/app.db"),
        vector_db_provider=os.getenv("VECTOR_DB_PROVIDER", "chroma"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
