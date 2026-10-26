"""
GET /api/v1/data-quality

Returns the five open data-quality items as structured objects.
Each item has a stable ID (DQI-01..DQI-05), severity, title, explanation,
entity_refs, source_refs, and navigation route.
No request-time free-form inference or fake entity IDs.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from infonet_api.config import get_cached_settings
from infonet_api.db.neo4j import execute_read_query, get_driver
from infonet_api.errors import (
    DATABASE_UNAVAILABLE,
    DATA_NOT_LOADED,
    error_response,
)

logger = logging.getLogger("infonet_api.routers.data_quality")

router = APIRouter()


def _db_available() -> bool:
    driver = get_driver()
    if driver is None:
        return False
    try:
        driver.verify_connectivity()
        return True
    except (ServiceUnavailable, Neo4jError):
        return False


def _data_loaded(database: str, timeout: int) -> bool:
    rows = execute_read_query(
        "MATCH (n:InfonetManaged:Entity) RETURN count(n) AS cnt",
        database=database,
        timeout=timeout,
    )
    return bool(rows and rows[0]["cnt"] > 0)


@router.get("/data-quality")
async def data_quality():
    """Returns the five open data-quality items."""
    settings = get_cached_settings()

    if not _db_available():
        return error_response(503, DATABASE_UNAVAILABLE, "Neo4j is unavailable.")

    try:
        db = settings.neo4j_database
        timeout = settings.infonet_query_timeout_s

        if not _data_loaded(db, timeout):
            return error_response(503, DATA_NOT_LOADED, "No INFONET data loaded.")

        # Query live counts / info to populate details
        rel_counts = execute_read_query(
            "MATCH (a:InfonetManaged:Entity)-[r]->(b:InfonetManaged:Entity) "
            "WHERE type(r) IN ['AFFILIATED_WITH','HAS_LABORATORY','OFFERS_PROGRAM','IS_HOD_OF'] "
            "RETURN count(r) AS total, "
            "       count(CASE WHEN r.confirmation_source = 'user_confirmed' THEN 1 END) AS user_confirmed",
            database=db,
            timeout=timeout,
        )
        total_rels = rel_counts[0]["total"] if rel_counts else 81
        user_conf_rels = rel_counts[0]["user_confirmed"] if rel_counts else 1
        inferred_rels = total_rels - user_conf_rels

        items: list[dict[str, Any]] = [
            {
                "id": "DQI-01",
                "kind": "source_claim",
                "origin": "pipeline_observation",
                "severity": "medium",
                "title": "Historical HOD Source Claim Unverified",
                "summary": (
                    "The historical brochure/catalog HOD statement in pipeline artifacts is an "
                    "unverified source claim contradicted by current department leadership. The "
                    "active HOD relationship (IS_HOD_OF for Dr. R. Sumathi) is user-confirmed "
                    "project data, not independent verification from an official institutional source."
                ),
                "explanation": (
                    "The historical brochure/catalog HOD statement in pipeline artifacts is an "
                    "unverified source claim contradicted by current department leadership. The "
                    "active HOD relationship (IS_HOD_OF for Dr. R. Sumathi) is user-confirmed "
                    "project data, not independent verification from an official institutional source."
                ),
                "entity_refs": ["DERIVED-PERSON-3e943445fa58", "DEPT-9d979a8ef1d6"],
                "source_refs": ["01-PRD.md §4", "05-Database-Design.md §2"],
                "route": "/entities/DERIVED-PERSON-3e943445fa58",
                "details": {
                    "active_hod_id": "DERIVED-PERSON-3e943445fa58",
                    "department_id": "DEPT-9d979a8ef1d6",
                    "relationship_type": "IS_HOD_OF",
                    "confirmation_source": "user_confirmed",
                    "confirmed_on": "2026-10-26",
                    "independent_source_verified": False,
                },
            },
            {
                "id": "DQI-02",
                "kind": "conflict",
                "origin": "pipeline_observation",
                "severity": "high",
                "title": "Conflicting Evening-Program Records",
                "summary": (
                    "Duplicate evening-program records exist with conflicting level (UG vs PG) "
                    "and duration (3 years vs 2 years). Both records are preserved until the discrepancy is resolved."
                ),
                "explanation": (
                    "Duplicate evening-program records exist with conflicting level (UG vs PG) "
                    "and duration (3 years vs 2 years). Both records are preserved until the discrepancy is resolved."
                ),
                "entity_refs": ["DERIVED-PROG-727a0dbda979", "DERIVED-PROG-6a45904664ab"],
                "source_refs": ["01-PRD.md §5", "source_observations/program_conflicts.csv"],
                "route": "/programs",
                "details": {
                    "conflict_group": "PROG-CONFLICT-001",
                    "conflicting_entity_ids": [
                        "DERIVED-PROG-727a0dbda979",
                        "DERIVED-PROG-6a45904664ab",
                    ],
                },
            },
            {
                "id": "DQI-03",
                "kind": "provenance_gap",
                "origin": "project_note",
                "severity": "medium",
                "title": "Ph.D. Program Missing Raw Extraction Record",
                "summary": (
                    "The Ph.D. program record exists in the saved normalized snapshot but "
                    "lacks a counterpart raw programs.jsonl record. Intake and duration fields are not recorded."
                ),
                "explanation": (
                    "The Ph.D. program record exists in the saved normalized snapshot but "
                    "lacks a counterpart raw programs.jsonl record. Intake and duration fields are not recorded."
                ),
                "entity_refs": ["DERIVED-PROG-2b4bf3aa5be2"],
                "source_refs": ["01-PRD.md §5", "PN-02"],
                "route": "/entities/DERIVED-PROG-2b4bf3aa5be2",
                "details": {
                    "program_id": "DERIVED-PROG-2b4bf3aa5be2",
                    "missing_fields": ["intake", "intake_count", "duration"],
                },
            },
            {
                "id": "DQI-04",
                "kind": "inferred_links",
                "origin": "project_note",
                "severity": "low",
                "title": "Department Relationships Inferred from Page Context",
                "summary": (
                    f"{inferred_rels} relationships are inferred from department page context "
                    f"and require review. {user_conf_rels} relationship (IS_HOD_OF) is a user-confirmed project assertion."
                ),
                "explanation": (
                    f"{inferred_rels} relationships are inferred from department page context "
                    f"and require review. {user_conf_rels} relationship (IS_HOD_OF) is a user-confirmed project assertion."
                ),
                "entity_refs": ["DEPT-9d979a8ef1d6"],
                "source_refs": ["05-Database-Design.md §3.2", "PN-04"],
                "route": "/graph",
                "details": {
                    "relationships_total": total_rels,
                    "relationships_inferred": inferred_rels,
                    "relationships_user_confirmed": user_conf_rels,
                },
            },
            {
                "id": "DQI-05",
                "kind": "summary_vs_table",
                "origin": "project_note",
                "severity": "medium",
                "title": "Department Description vs Program Table Discrepancy",
                "summary": (
                    "The department narrative description mentions three autonomous programs with a "
                    "present intake of 240, whereas the structured program table lists 7 programs. "
                    "No reconciliation has been computed."
                ),
                "explanation": (
                    "The department narrative description mentions three autonomous programs with a "
                    "present intake of 240, whereas the structured program table lists 7 programs. "
                    "No reconciliation has been computed."
                ),
                "entity_refs": ["DEPT-9d979a8ef1d6"],
                "source_refs": ["01-PRD.md §6", "PN-03"],
                "route": "/entities/DEPT-9d979a8ef1d6",
                "details": {
                    "department_id": "DEPT-9d979a8ef1d6",
                    "quotes": ["present intake of 240", "three autonomous programs"],
                },
            },
        ]

        return {
            "items": items,
            "total": len(items),
        }

    except (ServiceUnavailable, Neo4jError) as exc:
        logger.warning("Data quality query failed: %s", exc.__class__.__name__)
        return error_response(503, DATABASE_UNAVAILABLE, "Database query failed.")
