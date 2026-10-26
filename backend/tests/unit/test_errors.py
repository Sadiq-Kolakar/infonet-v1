"""
Unit tests for API error envelopes and validation error handling.
"""

from __future__ import annotations


def test_422_invalid_limit(client):
    """limit > 500 or limit < 1 must return 422 INVALID_PARAMETER envelope."""
    response = client.get("/api/v1/people?limit=999")
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_PARAMETER"
    assert "parameter" in data["error"]["details"]


def test_422_invalid_offset(client):
    """Negative offset must return 422 INVALID_PARAMETER envelope."""
    response = client.get("/api/v1/people?offset=-5")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INVALID_PARAMETER"


def test_422_invalid_sort(client):
    """Unsupported sort key must return 422 INVALID_PARAMETER."""
    response = client.get("/api/v1/people?sort=invalid_sort")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INVALID_PARAMETER"


def test_422_invalid_order(client):
    """Unsupported order must return 422 INVALID_PARAMETER."""
    response = client.get("/api/v1/people?order=sideways")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INVALID_PARAMETER"


def test_422_invalid_program_level(client):
    """Invalid level on /programs must return 422 INVALID_PARAMETER."""
    response = client.get("/api/v1/programs?level=HighSchool")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INVALID_PARAMETER"


def test_empty_query_string_is_treated_as_absent(client, mock_driver, monkeypatch):
    """Whitespace-only query string should not error; treated as absent."""
    import infonet_api.routers.people as people_router
    monkeypatch.setattr(people_router, "_db_available", lambda: True)
    monkeypatch.setattr(people_router, "_data_loaded", lambda db, to: True)
    monkeypatch.setattr(people_router, "execute_read_query", lambda *args, **kwargs: [])

    response = client.get("/api/v1/people?q=   ")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["items"] == []
