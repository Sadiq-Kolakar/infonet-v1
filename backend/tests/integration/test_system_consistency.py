"""
Targeted consistency and boundary tests for the INFONET API.

Verifies:
1. Consistency across summary counts, graph counts, people directory, and data-quality.
2. Pagination boundaries (limit 1, 500, 0, 501; offset 0, -1, 1000).
3. Missing entity 404 behavior.
4. Database-unavailable 503 behavior on data endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from infonet_api.app import app
from infonet_api.config import get_cached_settings
from infonet_api.db.neo4j import init_driver, close_driver, verify_connectivity
import infonet_api.db.neo4j as db_neo4j


@pytest.fixture
def live_client():
    settings = get_cached_settings()
    init_driver(settings)
    if not verify_connectivity(settings):
        close_driver()
        pytest.skip("Local Neo4j database is not available for integration testing.")
    with TestClient(app) as client:
        yield client
    close_driver()


def test_consistency_summary_and_graph(live_client):
    """Summary counts must match live graph counts and breakdown."""
    summary_res = live_client.get("/api/v1/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()

    graph_res = live_client.get("/api/v1/graph")
    assert graph_res.status_code == 200
    graph = graph_res.json()

    # Total counts match
    total_nodes = summary["counts"]["people"] + summary["counts"]["laboratories"] + summary["counts"]["programs"] + summary["department_count"]
    assert total_nodes == 81
    assert len(graph["nodes"]) == 81
    assert graph["meta"]["node_count"] == 81

    total_rels = summary["counts"]["relationships"]
    assert total_rels == 81
    assert len(graph["edges"]) == 81
    assert graph["meta"]["edge_count"] == 81

    # Breakdown matches
    assert summary["counts"]["people"] == 59
    assert summary["counts"]["faculty"] == 47
    assert summary["counts"]["support_staff"] == 12
    assert summary["counts"]["laboratories"] == 14
    assert summary["counts"]["programs"] == 7
    assert summary["data_status"]["relationships_user_confirmed"] == 1
    assert summary["data_status"]["relationships_inferred"] == 80


def test_consistency_node_and_edge_types(live_client):
    """Only approved entity and relationship types exist in the live graph."""
    res = live_client.get("/api/v1/graph")
    assert res.status_code == 200
    graph = res.json()

    node_types = {n["data"]["type"] for n in graph["nodes"]}
    assert node_types == {"Department", "Person", "Laboratory", "Program"}

    edge_types = {e["data"]["type"] for e in graph["edges"]}
    assert edge_types == {"AFFILIATED_WITH", "HAS_LABORATORY", "OFFERS_PROGRAM", "IS_HOD_OF"}

    # Count by type
    type_counts = {}
    for n in graph["nodes"]:
        t = n["data"]["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    assert type_counts == {"Department": 1, "Person": 59, "Laboratory": 14, "Program": 7}

    rel_counts = {}
    for e in graph["edges"]:
        t = e["data"]["type"]
        rel_counts[t] = rel_counts.get(t, 0) + 1
    assert rel_counts == {"AFFILIATED_WITH": 59, "HAS_LABORATORY": 14, "OFFERS_PROGRAM": 7, "IS_HOD_OF": 1}


def test_consistency_data_quality_endpoint(live_client):
    """Data quality endpoint reflects 5 items consistent with graph and summary."""
    res = live_client.get("/api/v1/data-quality")
    assert res.status_code == 200
    dq = res.json()
    assert dq["total"] == 5

    items = {item["id"]: item for item in dq["items"]}
    assert set(items.keys()) == {"DQI-01", "DQI-02", "DQI-03", "DQI-04", "DQI-05"}

    # DQI-01 specifies user-confirmed HOD override
    assert "user-confirmed" in items["DQI-01"]["explanation"]
    assert "Dr. R. Sumathi" in items["DQI-01"]["explanation"]

    # DQI-04 specifies 80 inferred and 1 user-confirmed relationship
    assert "80 relationships are inferred" in items["DQI-04"]["explanation"]
    assert "1 relationship (IS_HOD_OF) is a user-confirmed project assertion" in items["DQI-04"]["explanation"]


def test_pagination_boundaries(live_client):
    """Test limit and offset valid boundaries and invalid error envelopes."""
    # Valid limit=1
    res = live_client.get("/api/v1/people?limit=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    assert data["total"] == 59
    assert data["limit"] == 1

    # Valid limit=500
    res = live_client.get("/api/v1/people?limit=500")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 59
    assert data["limit"] == 500

    # Invalid limit=0 -> 422
    res = live_client.get("/api/v1/people?limit=0")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "INVALID_PARAMETER"

    # Invalid limit=501 -> 422
    res = live_client.get("/api/v1/people?limit=501")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "INVALID_PARAMETER"

    # Valid offset=0
    res = live_client.get("/api/v1/people?offset=0")
    assert res.status_code == 200

    # Invalid offset=-1 -> 422
    res = live_client.get("/api/v1/people?offset=-1")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "INVALID_PARAMETER"

    # Offset beyond total -> returns empty list with total=59
    res = live_client.get("/api/v1/people?offset=1000")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 59


def test_missing_entity_404(live_client):
    """Querying an unknown entity ID returns 404 NOT_FOUND."""
    res = live_client.get("/api/v1/entities/NON-EXISTENT-ENTITY-ID-999")
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["details"]["id"] == "NON-EXISTENT-ENTITY-ID-999"


def test_database_unavailable_returns_503(client):
    """When DB is unavailable, data endpoints return 503 DATABASE_UNAVAILABLE."""
    db_neo4j._driver = None  # Force database unavailable

    for endpoint in ("/api/v1/summary", "/api/v1/about", "/api/v1/people", "/api/v1/laboratories", "/api/v1/programs", "/api/v1/entities/DEPT-9d979a8ef1d6", "/api/v1/graph", "/api/v1/data-quality"):
        res = client.get(endpoint)
        assert res.status_code == 503, f"{endpoint} expected 503 but got {res.status_code}"
        data = res.json()
        assert data["error"]["code"] == "DATABASE_UNAVAILABLE"
