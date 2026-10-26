"""
Unit tests for GET /api/v1/health endpoint.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from neo4j.exceptions import ServiceUnavailable

import infonet_api.db.neo4j as db_neo4j


def test_health_database_down(client):
    """When driver is not initialized or database is down, returns 200 with database='down'."""
    db_neo4j._driver = None
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] == "up"
    assert data["database"] == "down"
    assert data["data_loaded"] is False


def test_health_database_up_no_data(client, mock_driver):
    """When DB is connected but no entity data found, data_loaded=False."""
    session_mock = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = session_mock
    # execute_read returns cnt = 0
    session_mock.execute_read.return_value = {"cnt": 0}

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] == "up"
    assert data["database"] == "up"
    assert data["data_loaded"] is False


def test_health_database_up_with_data(client, mock_driver):
    """When DB is connected and data exists, data_loaded=True."""
    session_mock = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = session_mock
    session_mock.execute_read.return_value = {"cnt": 81}

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] == "up"
    assert data["database"] == "up"
    assert data["data_loaded"] is True


def test_health_never_exposes_credentials(client):
    """Health response body must never contain sensitive keys."""
    response = client.get("/api/v1/health")
    text = response.text.lower()
    assert "password" not in text
    assert "secret" not in text
    assert "neo4j://" not in text
