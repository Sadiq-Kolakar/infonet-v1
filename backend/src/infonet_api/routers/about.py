"""
GET /api/v1/about

Returns pipeline/run metadata, MVP scope statements, and the list of
known data limitations and caveats.  Values come from the loaded graph
(when available) and maintained project configuration — nothing is
fabricated.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from infonet_api.config import get_cached_settings
from infonet_api.db.neo4j import execute_read_query, get_driver
from infonet_api.errors import (
    DATABASE_UNAVAILABLE,
    DATA_NOT_LOADED,
    error_response,
)

logger = logging.getLogger("infonet_api.routers.about")

router = APIRouter()

# ── Static scope statements (maintained project config) ──────────────

_SCOPE = {
    "institution": "Siddaganga Institute of Technology (SIT), Tumakuru",
    "department": "Computer Science & Engineering",
    "scope": "CSE-only MVP",
    "language": "English only",
    "access_mode": "Read-only, local deployment",
    "data_source": (
        "Normalized dataset from the Stage-1 extraction/normalization pipeline, "
        "supplemented by explicit, version-controlled project overrides "
        "(e.g., user-confirmed HOD appointment)."
    ),
}

_KNOWN_LIMITATIONS = [
    {
        "id": "LIM-01",
        "title": "No independent verification",
        "description": (
            "All current records require review. None has been independently "
            "verified by an official institutional audit."
        ),
    },
    {
        "id": "LIM-02",
        "title": "Inferred relationships need review",
        "description": (
            "80 of 81 relationships are inferred from page context and flagged "
            "for review. 1 relationship (IS_HOD_OF) is user-confirmed project "
            "data, not independently source-verified."
        ),
    },
    {
        "id": "LIM-03",
        "title": "Duplicate evening-program records",
        "description": (
            "Two evening-program records exist with conflicting UG/PG level "
            "and duration. Both are preserved until the discrepancy is resolved."
        ),
    },
    {
        "id": "LIM-04",
        "title": "Ph.D. program missing raw record",
        "description": (
            "The Ph.D. program record exists in the normalized snapshot but "
            "lacks a counterpart raw programs.jsonl record."
        ),
    },
    {
        "id": "LIM-05",
        "title": "Department description vs. program table discrepancy",
        "description": (
            "The department narrative text and the structured program list "
            "contain conflicting information about autonomous programs and intake."
        ),
    },
    {
        "id": "LIM-06",
        "title": "CSE-only scope",
        "description": (
            "Only the CSE department has been normalized, despite raw candidates "
            "mentioning other departments."
        ),
    },
    {
        "id": "LIM-07",
        "title": "Page-level provenance",
        "description": (
            "Provenance is page-level, not record-specific evidence. Where "
            "evidence text is not stored, evidence_note is set to "
            "'no_evidence_text_stored'."
        ),
    },
]


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


@router.get("/about")
async def about():
    """Application metadata, scope, and known limitations."""
    settings = get_cached_settings()

    if not _db_available():
        return error_response(503, DATABASE_UNAVAILABLE, "Neo4j is unavailable.")

    db = settings.neo4j_database
    timeout = settings.infonet_query_timeout_s

    try:
        if not _data_loaded(db, timeout):
            return error_response(503, DATA_NOT_LOADED, "No INFONET data loaded.")

        # Try to read PipelineRun metadata if it exists
        run_rows = execute_read_query(
            "MATCH (r:InfonetManaged:PipelineRun) "
            "RETURN r.run_id AS run_id, r.run_timestamp AS run_timestamp, "
            "       r.pipeline_version AS pipeline_version, "
            "       r.source_hash AS source_hash "
            "ORDER BY r.run_timestamp DESC LIMIT 1",
            database=db,
            timeout=timeout,
        )
        pipeline_run = None
        if run_rows:
            row = run_rows[0]
            pipeline_run = {
                "run_id": row.get("run_id"),
                "run_timestamp": str(row["run_timestamp"]) if row.get("run_timestamp") else None,
                "pipeline_version": row.get("pipeline_version"),
                "source_hash": row.get("source_hash"),
            }

        return {
            "scope": _SCOPE,
            "pipeline_run": pipeline_run,
            "known_limitations": _KNOWN_LIMITATIONS,
        }

    except (ServiceUnavailable, Neo4jError) as exc:
        logger.warning("About query failed: %s", exc.__class__.__name__)
        return error_response(503, DATABASE_UNAVAILABLE, "Database query failed.")
