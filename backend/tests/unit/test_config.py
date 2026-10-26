"""
Unit tests for configuration loading and validation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from infonet_common.settings import Settings


def test_settings_valid(monkeypatch):
    """Test valid settings instantiation from environment."""
    monkeypatch.setenv("NEO4J_URI", "neo4j://localhost:7687")
    monkeypatch.setenv("NEO4J_USERNAME", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret123")
    monkeypatch.setenv("NEO4J_DATABASE", "neo4j")
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("API_PORT", "8000")
    monkeypatch.setenv("INFONET_QUERY_TIMEOUT_S", "5")

    s = Settings()
    assert s.neo4j_uri == "neo4j://localhost:7687"
    assert s.neo4j_username == "neo4j"
    assert s.neo4j_password == "secret123"
    assert s.neo4j_database == "neo4j"
    assert s.api_host == "127.0.0.1"
    assert s.api_port == 8000
    assert s.infonet_query_timeout_s == 5


def test_settings_missing_password(monkeypatch):
    """Fails fast when required password is missing."""
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    # Ensure no .env file interferes
    monkeypatch.setattr(Settings, "model_config", {"env_file": None, "extra": "ignore"})
    with pytest.raises(ValidationError):
        Settings()
