"""
Integration tests for GET /api/v1/graph against the live Neo4j dataset.

Verifies:
- 81 nodes and 81 edges
- Four approved relationship types: AFFILIATED_WITH, HAS_LABORATORY, IS_HOD_OF, OFFERS_PROGRAM
- IS_HOD_OF regression assertions:
  * Correct source (DERIVED-PERSON-3e943445fa58) and target (DEPT-9d979a8ef1d6)
  * status_code is 'user_confirmed_assertion'
  * confirmation_source is 'user_confirmed'
  * independent_source_verified is False
  * confirmed_on is an ISO 8601 string in YYYY-MM-DD format
"""

from __future__ import annotations

import re
import pytest
from fastapi.testclient import TestClient

from infonet_api.app import app
from infonet_api.config import get_cached_settings
from infonet_api.db.neo4j import init_driver, close_driver, verify_connectivity


@pytest.fixture
def live_client():
    """Client connected to the live database if available."""
    settings = get_cached_settings()
    driver = init_driver(settings)
    if not verify_connectivity(settings):
        close_driver()
        pytest.skip("Local Neo4j database is not available for integration testing.")

    with TestClient(app) as client:
        yield client

    close_driver()


def test_live_graph_81_nodes_81_edges(live_client):
    """The graph endpoint must return 81 nodes and 81 edges on the live dataset."""
    response = live_client.get("/api/v1/graph")
    assert response.status_code == 200
    data = response.json()

    nodes = data["nodes"]
    edges = data["edges"]
    meta = data["meta"]

    # Graph counts
    assert len(nodes) == 81, f"Expected 81 nodes, got {len(nodes)}"
    assert len(edges) == 81, f"Expected 81 edges, got {len(edges)}"
    assert meta["node_count"] == 81
    assert meta["edge_count"] == 81

    # Relationship types
    expected_types = ["AFFILIATED_WITH", "HAS_LABORATORY", "IS_HOD_OF", "OFFERS_PROGRAM"]
    assert meta["relationship_types"] == expected_types


def test_live_graph_is_hod_of_edge_regression(live_client):
    """Regression test for the user-confirmed IS_HOD_OF relationship."""
    response = live_client.get("/api/v1/graph")
    assert response.status_code == 200
    data = response.json()

    hod_edges = [e for e in data["edges"] if e["data"]["type"] == "IS_HOD_OF"]
    assert len(hod_edges) == 1, f"Expected exactly 1 IS_HOD_OF edge, found {len(hod_edges)}"

    hod_data = hod_edges[0]["data"]

    # 1. Correct source and target IDs
    assert hod_data["source"] == "DERIVED-PERSON-3e943445fa58"
    assert hod_data["target"] == "DEPT-9d979a8ef1d6"

    # 2. status_code is user_confirmed_assertion
    assert hod_data["status_code"] == "user_confirmed_assertion"

    # 3. confirmation_source is user_confirmed
    assert hod_data["confirmation_source"] == "user_confirmed"

    # 4. independent_source_verified is false
    assert hod_data["independent_source_verified"] is False

    # 5. confirmed_on is an ISO 8601 string in YYYY-MM-DD format
    confirmed_on = hod_data["confirmed_on"]
    assert isinstance(confirmed_on, str), f"confirmed_on should be a string, got {type(confirmed_on)}"
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", confirmed_on), (
        f"confirmed_on '{confirmed_on}' does not match YYYY-MM-DD format"
    )
    assert confirmed_on == "2026-10-26"
