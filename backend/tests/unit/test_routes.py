"""
Unit tests for all API endpoints using mocked Neo4j responses.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock
from neo4j.time import Date
import pytest


# ── About ─────────────────────────────────────────────────────────────

def test_about_endpoint(client, mock_driver, monkeypatch):
    """GET /api/v1/about returns scope statements and 7 known limitations."""
    import infonet_api.routers.about as about_router
    monkeypatch.setattr(about_router, "_db_available", lambda: True)
    monkeypatch.setattr(about_router, "_data_loaded", lambda db, to: True)
    monkeypatch.setattr(about_router, "execute_read_query", lambda *args, **kwargs: [])

    response = client.get("/api/v1/about")
    assert response.status_code == 200
    data = response.json()
    assert "scope" in data
    assert data["scope"]["department"] == "Computer Science & Engineering"
    assert "known_limitations" in data
    assert len(data["known_limitations"]) == 7


# ── Summary ───────────────────────────────────────────────────────────

def test_summary_endpoint(client, mock_driver, monkeypatch):
    """GET /api/v1/summary calculates counts from live DB queries."""
    import infonet_api.routers.summary as summary_router
    monkeypatch.setattr(summary_router, "_db_available", lambda: True)
    monkeypatch.setattr(summary_router, "_data_loaded", lambda db, to: True)

    def mock_query(q, parameters=None, **kwargs):
        if "MATCH (d:InfonetManaged:Entity:Department) RETURN d.id" in q:
            return [{"id": "DEPT-9d979a8ef1d6", "name": "CSE", "description": None, "source_url": None}]
        if "MATCH (d:InfonetManaged:Entity:Department) RETURN count(d)" in q:
            return [{"cnt": 1}]
        if "MATCH (p:InfonetManaged:Entity:Person)" in q:
            return [{"total": 59, "support_staff": 12}]
        if "MATCH (l:InfonetManaged:Entity:Laboratory)" in q:
            return [{"cnt": 14}]
        if "MATCH (pr:InfonetManaged:Entity:Program)" in q:
            return [{"cnt": 7}]
        if "MATCH (a:InfonetManaged:Entity)-[r]->(b:InfonetManaged:Entity)" in q:
            return [{"total": 81, "user_confirmed": 1}]
        if "MATCH (h:InfonetManaged:HodClaim)" in q:
            return [{"cnt": 1}]
        if "MATCH (c:InfonetManaged:ProgramConflict)" in q:
            return [{"cnt": 1}]
        return []

    monkeypatch.setattr(summary_router, "execute_read_query", mock_query)

    response = client.get("/api/v1/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["department_count"] == 1
    assert data["counts"]["people"] == 59
    assert data["counts"]["faculty"] == 47
    assert data["counts"]["support_staff"] == 12
    assert data["counts"]["laboratories"] == 14
    assert data["counts"]["programs"] == 7
    assert data["counts"]["relationships"] == 81
    assert data["data_status"]["relationships_user_confirmed"] == 1
    assert data["data_status"]["relationships_inferred"] == 80
    assert data["data_status"]["open_data_quality_items"] == 5


# ── People ────────────────────────────────────────────────────────────

def test_people_endpoint(client, mock_driver, monkeypatch):
    """GET /api/v1/people returns paginated list envelope with facets."""
    import infonet_api.routers.people as people_router
    monkeypatch.setattr(people_router, "_db_available", lambda: True)
    monkeypatch.setattr(people_router, "_data_loaded", lambda db, to: True)

    mock_records = [
        {
            "id": "DERIVED-PERSON-3e943445fa58",
            "name": "Dr. R Sumathi",
            "role_title": "Professor & Head",
            "person_category": "Teaching Faculty",
            "directory_category": "Faculty",
            "resume_url": "https://sit.ac.in/resume.pdf",
            "department_id": "DEPT-9d979a8ef1d6",
            "extraction_status": "derived_from_saved_snapshot_needs_review",
            "department_link_status": "inferred_from_cse_department_page_needs_review",
            "source_url": "https://sit.ac.in",
            "source_section": "faculty",
            "source_evidence": "Dr. R. Sumathi",
            "content_hash": "abc123hash",
        }
    ]
    monkeypatch.setattr(people_router, "execute_read_query", lambda *args, **kwargs: mock_records)

    response = client.get("/api/v1/people?q=Sumathi")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["id"] == "DERIVED-PERSON-3e943445fa58"
    assert item["name"] == "Dr. R Sumathi"
    assert item["attributes"]["resume_url"] == "https://sit.ac.in/resume.pdf"
    assert "facets" in data
    assert "person_category" in data["facets"]


# ── Laboratories ──────────────────────────────────────────────────────

def test_laboratories_endpoint(client, mock_driver, monkeypatch):
    """GET /api/v1/laboratories returns laboratory directory."""
    import infonet_api.routers.laboratories as lab_router
    monkeypatch.setattr(lab_router, "_db_available", lambda: True)
    monkeypatch.setattr(lab_router, "_data_loaded", lambda db, to: True)

    mock_labs = [
        {
            "id": "LAB-001",
            "name": "Microprocessor Laboratory",
            "department_id": "DEPT-9d979a8ef1d6",
            "extraction_method": "table_extraction",
            "extraction_status": "derived_from_saved_snapshot_needs_review",
            "department_link_status": "inferred_from_cse_department_page_needs_review",
            "source_url": "https://sit.ac.in",
            "source_section": "labs",
            "content_hash": "labhash",
        }
    ]
    monkeypatch.setattr(lab_router, "execute_read_query", lambda *args, **kwargs: mock_labs)

    response = client.get("/api/v1/laboratories")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Microprocessor Laboratory"


# ── Programs ──────────────────────────────────────────────────────────

def test_programs_endpoint(client, mock_driver, monkeypatch):
    """GET /api/v1/programs supports level filtering and conflict visibility."""
    import infonet_api.routers.programs as prog_router
    monkeypatch.setattr(prog_router, "_db_available", lambda: True)
    monkeypatch.setattr(prog_router, "_data_loaded", lambda db, to: True)

    mock_progs = [
        {
            "id": "DERIVED-PROG-727a0dbda979",
            "name": "B.E. Computer Science and Engineering (Evening)",
            "level": "UG",
            "intake": "18",
            "intake_count": 18,
            "duration": "3 years",
            "department_id": "DEPT-9d979a8ef1d6",
            "conflict_group": "PROG-CONFLICT-001",
            "extraction_method": "table_extraction",
            "extraction_status": "derived_from_saved_snapshot_needs_review",
            "department_link_status": "inferred_from_cse_department_page_needs_review",
            "source_url": "https://sit.ac.in",
            "source_section": "programs",
            "source_evidence": "B.E. Evening",
            "content_hash": "prog_hash",
        }
    ]
    monkeypatch.setattr(prog_router, "execute_read_query", lambda *args, **kwargs: mock_progs)

    response = client.get("/api/v1/programs?level=UG")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["attributes"]["conflict_group"] == "PROG-CONFLICT-001"
    assert item["conflict"] is not None
    assert item["conflict"]["id"] == "PROG-CONFLICT-001"


# ── Entity Detail ─────────────────────────────────────────────────────

def test_entity_detail_404(client, mock_driver, monkeypatch):
    """GET /api/v1/entities/{unknown_id} returns 404 NOT_FOUND."""
    import infonet_api.routers.entities as entities_router
    monkeypatch.setattr(entities_router, "_db_available", lambda: True)
    monkeypatch.setattr(entities_router, "_data_loaded", lambda db, to: True)
    monkeypatch.setattr(entities_router, "execute_read_query", lambda *args, **kwargs: [])

    response = client.get("/api/v1/entities/NON-EXISTENT-ID")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"


def test_entity_detail_person_with_hod(client, mock_driver, monkeypatch):
    """Dr. R. Sumathi entity detail includes IS_HOD_OF and HodClaim observation."""
    import infonet_api.routers.entities as entities_router
    monkeypatch.setattr(entities_router, "_db_available", lambda: True)
    monkeypatch.setattr(entities_router, "_data_loaded", lambda db, to: True)

    def mock_query(q, parameters=None, **kwargs):
        if "MATCH (n:InfonetManaged:Entity {id: $id})" in q and "labels(n)" in q:
            return [{
                "props": {
                    "id": "DERIVED-PERSON-3e943445fa58",
                    "name": "Dr. R Sumathi",
                    "role_title": "Professor & Head",
                    "person_category": "Teaching Faculty",
                    "directory_category": "Faculty",
                    "resume_url": "https://sit.ac.in/resume.pdf",
                    "department_id": "DEPT-9d979a8ef1d6",
                    "extraction_status": "derived_from_saved_snapshot_needs_review",
                    "department_link_status": "inferred_from_cse_department_page_needs_review",
                    "source_url": "https://sit.ac.in",
                    "source_section": "faculty",
                    "source_evidence": "Dr. R. Sumathi",
                    "content_hash": "hash_sumathi",
                },
                "labels": ["InfonetManaged", "Entity", "Person"],
            }]
        if "MATCH (n:InfonetManaged:Entity {id: $id})-[r]-(m:InfonetManaged:Entity)" in q:
            return [
                {
                    "rel_type": "AFFILIATED_WITH",
                    "is_outgoing": True,
                    "related_id": "DEPT-9d979a8ef1d6",
                    "related_name": "Computer Science & Engineering",
                    "related_type": "Department",
                    "rel_props": {
                        "confidence_status": "inferred_from_cse_department_page_needs_review",
                        "source_url": "https://sit.ac.in",
                    },
                },
                {
                    "rel_type": "IS_HOD_OF",
                    "is_outgoing": True,
                    "related_id": "DEPT-9d979a8ef1d6",
                    "related_name": "Computer Science & Engineering",
                    "related_type": "Department",
                    "rel_props": {
                        "confirmation_source": "user_confirmed",
                        "confirmed_on": "2026-10-26",
                        "independent_source_verified": False,
                    },
                },
            ]
        if "MATCH (h:InfonetManaged:HodClaim)" in q:
            return [{
                "props": {
                    "id": "HOD-CLAIM-001",
                    "claim_status": "unverified_source_claim",
                    "person_name": "Dr. R Sumathi",
                    "role_title": "Head of Department",
                    "source_evidence": "Brochure text",
                    "source_url": "https://sit.ac.in",
                }
            }]
        return []

    monkeypatch.setattr(entities_router, "execute_read_query", mock_query)

    response = client.get("/api/v1/entities/DERIVED-PERSON-3e943445fa58")
    assert response.status_code == 200
    data = response.json()
    assert data["entity"]["name"] == "Dr. R Sumathi"
    assert data["entity"]["type"] == "Person"

    # Verify IS_HOD_OF relationship
    assert len(data["related"]["is_hod_of"]) == 1
    hod_rel = data["related"]["is_hod_of"][0]
    assert hod_rel["direction"] == "outgoing"
    assert hod_rel["status_code"] == "user_confirmed_assertion"
    assert hod_rel["confirmation_source"] == "user_confirmed"
    assert hod_rel["confirmed_on"] == "2026-10-26"
    assert hod_rel["independent_source_verified"] is False

    # Verify HodClaim observation is unverified
    assert len(data["observations"]) == 1
    obs = data["observations"][0]
    assert obs["observation_type"] == "HodClaim"
    assert obs["status_code"] == "unverified_claim"
    assert obs["claim_promoted_to_relationship"] is False


# ── Graph ─────────────────────────────────────────────────────────────

def test_graph_endpoint(client, mock_driver, monkeypatch):
    """GET /api/v1/graph returns Cytoscape envelope with approved edges and metadata."""
    import infonet_api.routers.graph as graph_router
    monkeypatch.setattr(graph_router, "_db_available", lambda: True)
    monkeypatch.setattr(graph_router, "_data_loaded", lambda db, to: True)

    def mock_query(q, **kwargs):
        if "MATCH (n:InfonetManaged:Entity)" in q:
            return [
                {
                    "id": "DEPT-9d979a8ef1d6",
                    "name": "CSE",
                    "labels": ["InfonetManaged", "Entity", "Department"],
                    "extraction_status": None,
                },
                {
                    "id": "DERIVED-PERSON-3e943445fa58",
                    "name": "Dr. R Sumathi",
                    "labels": ["InfonetManaged", "Entity", "Person"],
                    "extraction_status": "derived_from_saved_snapshot_needs_review",
                },
            ]
        if "MATCH (a:InfonetManaged:Entity)-[r]->(b:InfonetManaged:Entity)" in q:
            return [
                {
                    "source": "DERIVED-PERSON-3e943445fa58",
                    "target": "DEPT-9d979a8ef1d6",
                    "rel_type": "AFFILIATED_WITH",
                    "rel_props": {
                        "confidence_status": "inferred_from_cse_department_page_needs_review",
                        "source_url": "https://sit.ac.in",
                    },
                },
                {
                    "source": "DERIVED-PERSON-3e943445fa58",
                    "target": "DEPT-9d979a8ef1d6",
                    "rel_type": "IS_HOD_OF",
                    "rel_props": {
                        "id": "OVERRIDE-IS-HOD-OF-DERIVED-PERSON-3e943445fa58-DEPT-9d979a8ef1d6",
                        "confirmation_source": "user_confirmed",
                        "confirmed_on": Date(2026, 10, 26),
                        "independent_source_verified": False,
                    },
                },
            ]
        return []

    monkeypatch.setattr(graph_router, "execute_read_query", mock_query)

    response = client.get("/api/v1/graph")
    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 2
    assert data["meta"]["node_count"] == 2
    assert data["meta"]["edge_count"] == 2
    assert "IS_HOD_OF" in data["meta"]["relationship_types"]
    assert "AFFILIATED_WITH" in data["meta"]["relationship_types"]

    # Verify IS_HOD_OF edge regression checks
    hod_edge = [e for e in data["edges"] if e["data"]["type"] == "IS_HOD_OF"][0]["data"]
    assert hod_edge["source"] == "DERIVED-PERSON-3e943445fa58"
    assert hod_edge["target"] == "DEPT-9d979a8ef1d6"
    assert hod_edge["status_code"] == "user_confirmed_assertion"
    assert hod_edge["confirmation_source"] == "user_confirmed"
    assert hod_edge["independent_source_verified"] is False
    assert isinstance(hod_edge["confirmed_on"], str)
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", hod_edge["confirmed_on"])
    assert hod_edge["confirmed_on"] == "2026-10-26"


def test_graph_endpoint_81_dataset_mock(client, mock_driver, monkeypatch):
    """Regression test ensuring 81 nodes and 81 edges contract with IS_HOD_OF edge."""
    from neo4j.time import Date
    import infonet_api.routers.graph as graph_router
    monkeypatch.setattr(graph_router, "_db_available", lambda: True)
    monkeypatch.setattr(graph_router, "_data_loaded", lambda db, to: True)

    mock_nodes = [{"id": f"NODE-{i}", "name": f"Node {i}", "labels": ["InfonetManaged", "Entity", "Person"], "extraction_status": None} for i in range(80)]
    mock_nodes.append({"id": "DEPT-9d979a8ef1d6", "name": "CSE", "labels": ["InfonetManaged", "Entity", "Department"], "extraction_status": None})

    mock_edges = [
        {"source": f"NODE-{i}", "target": "DEPT-9d979a8ef1d6", "rel_type": "AFFILIATED_WITH", "rel_props": {"confidence_status": "inferred_from_cse_department_page_needs_review"}}
        for i in range(80)
    ]
    mock_edges.append({
        "source": "DERIVED-PERSON-3e943445fa58",
        "target": "DEPT-9d979a8ef1d6",
        "rel_type": "IS_HOD_OF",
        "rel_props": {
            "id": "OVERRIDE-IS-HOD-OF-DERIVED-PERSON-3e943445fa58-DEPT-9d979a8ef1d6",
            "confirmation_source": "user_confirmed",
            "confirmed_on": Date(2026, 10, 26),
            "independent_source_verified": False,
        },
    })

    def mock_query(q, **kwargs):
        if "MATCH (n:InfonetManaged:Entity)" in q:
            return mock_nodes
        if "MATCH (a:InfonetManaged:Entity)-[r]->(b:InfonetManaged:Entity)" in q:
            return mock_edges
        return []

    monkeypatch.setattr(graph_router, "execute_read_query", mock_query)

    response = client.get("/api/v1/graph")
    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) == 81
    assert len(data["edges"]) == 81
    assert data["meta"]["node_count"] == 81
    assert data["meta"]["edge_count"] == 81
    assert "IS_HOD_OF" in data["meta"]["relationship_types"]

    hod_edge = [e for e in data["edges"] if e["data"]["type"] == "IS_HOD_OF"][0]["data"]
    assert hod_edge["source"] == "DERIVED-PERSON-3e943445fa58"
    assert hod_edge["target"] == "DEPT-9d979a8ef1d6"
    assert hod_edge["status_code"] == "user_confirmed_assertion"
    assert hod_edge["confirmation_source"] == "user_confirmed"
    assert hod_edge["independent_source_verified"] is False
    assert isinstance(hod_edge["confirmed_on"], str)
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", hod_edge["confirmed_on"])
    assert hod_edge["confirmed_on"] == "2026-10-26"


# ── Data Quality ──────────────────────────────────────────────────────

def test_data_quality_endpoint(client, mock_driver, monkeypatch):
    """GET /api/v1/data-quality returns the 5 structured items with stable IDs."""
    import infonet_api.routers.data_quality as dq_router
    monkeypatch.setattr(dq_router, "_db_available", lambda: True)
    monkeypatch.setattr(dq_router, "_data_loaded", lambda db, to: True)
    monkeypatch.setattr(dq_router, "execute_read_query", lambda *args, **kwargs: [{"total": 81, "user_confirmed": 1}])

    response = client.get("/api/v1/data-quality")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    ids = [item["id"] for item in data["items"]]
    assert ids == ["DQI-01", "DQI-02", "DQI-03", "DQI-04", "DQI-05"]

    dqi1 = data["items"][0]
    assert dqi1["kind"] == "source_claim"
    assert "Dr. R. Sumathi" in dqi1["explanation"]

    dqi4 = data["items"][3]
    assert dqi4["kind"] == "inferred_links"
    assert "80 relationships are inferred" in dqi4["explanation"]
