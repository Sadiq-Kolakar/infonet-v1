"""
Application settings loaded from environment variables / .env file.

Uses pydantic-settings for validated, typed configuration.  The .env file
is loaded automatically when present; real credentials must never appear in
committed files, logs, or error responses.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Neo4j connection
    neo4j_uri: str = "neo4j://127.0.0.1:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str  # required — no default; fail fast if missing
    neo4j_database: str = "neo4j"

    # API server
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Query behaviour
    infonet_query_timeout_s: int = 5


def get_settings() -> Settings:
    """Create a new Settings instance (reads env vars / .env each time)."""
    return Settings()  # type: ignore[call-arg]
