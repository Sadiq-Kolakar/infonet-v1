"""
Pytest configuration and shared fixtures for INFONET API tests.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from dotenv import dotenv_values

# Load values from .env if present, otherwise fallback to test defaults
_local_env = dotenv_values(".env")

os.environ.setdefault("NEO4J_URI", _local_env.get("NEO4J_URI") or "neo4j://127.0.0.1:7687")
os.environ.setdefault("NEO4J_USERNAME", _local_env.get("NEO4J_USERNAME") or "neo4j")
if _local_env.get("NEO4J_PASSWORD"):
    os.environ.setdefault("NEO4J_PASSWORD", _local_env["NEO4J_PASSWORD"])
else:
    os.environ.setdefault("NEO4J_PASSWORD", "test-password-mock")
os.environ.setdefault("NEO4J_DATABASE", _local_env.get("NEO4J_DATABASE") or "neo4j")
os.environ.setdefault("INFONET_QUERY_TIMEOUT_S", _local_env.get("INFONET_QUERY_TIMEOUT_S") or "5")

from infonet_api.app import app
import infonet_api.db.neo4j as db_neo4j


@pytest.fixture(autouse=True)
def reset_db_driver():
    """Ensure driver is cleanly closed between tests."""
    yield
    db_neo4j.close_driver()


@pytest.fixture
def client():
    """FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_driver():
    """Mock Neo4j driver that reports connected."""
    mock = MagicMock()
    mock.verify_connectivity.return_value = None
    db_neo4j._driver = mock
    return mock
