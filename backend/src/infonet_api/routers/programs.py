"""
GET /api/v1/programs

Program directory with level filter, search, and pagination.
Preserves both evening-program records and the Ph.D. missing fields.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, Query
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from infonet_api.config import get_cached_settings
from infonet_api.db.neo4j import execute_read_query, get_driver
from infonet_api.errors import (
    DATABASE_UNAVAILABLE,
    DATA_NOT_LOADED,
    INVALID_PARAMETER,
    error_response,
)
from infonet_common.status_mapping import map_entity_display_code

logger = logging.getLogger("infonet_api.routers.programs")

router = APIRouter()

_VALID_LEVELS = frozenset({"UG", "PG", "Research"})

_PROG_PROVENANCE_FIELDS = (
    "source_url", "source_section", "source_evidence",
    "content_hash", "extraction_method", "extraction_status",
    "department_link_status",
)

_PROG_ALL_EXPECTED = {
    "name", "level", "intake", "intake_count", "duration",
    "department_id",
}


def _search_matches(name_lower: str, query_trimmed: str) -> tuple[bool, bool]:
    query_lower = query_trimmed.lower()
    tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", query_lower) if t]
    if not tokens:
        return True, False
    for token in tokens:
        if token not in name_lower:
            return False, False
    contiguous = query_lower in name_lower
    return True, contiguous


def _build_program_item(record: dict[str, Any]) -> dict[str, Any]:
    extraction_status = record.get("extraction_status")
    display_code = map_entity_display_code(extraction_status)

    attributes: dict[str, Any] = {
        "level": record.get("level"),
        "intake": record.get("intake"),
        "intake_count": record.get("intake_count"),
        "duration": record.get("duration"),
        "department_id": record.get("department_id"),
        "conflict_group": record.get("conflict_group"),
    }

    missing_fields = [
        f for f in _PROG_ALL_EXPECTED
        if record.get(f) is None or record.get(f) == ""
    ]

    provenance: dict[str, Any] = {}
    for f in _PROG_PROVENANCE_FIELDS:
        provenance[f] = record.get(f)

    status: dict[str, Any] = {
        "raw": {},
        "display_codes": [display_code],
    }
    if extraction_status:
        status["raw"]["extraction_status"] = extraction_status
    dept_link_status = record.get("department_link_status")
    if dept_link_status:
        status["raw"]["department_link_status"] = dept_link_status

    badges = [{"code": display_code}]
    if extraction_status:
        badges[0]["source_field"] = "extraction_status"
        badges[0]["raw_value"] = extraction_status

    # Conflict info
    conflict_group = record.get("conflict_group")
    conflict = None
    if conflict_group:
        conflict = {
            "id": conflict_group,
            "conflict_group": conflict_group,
            "resolution_status": "unresolved_preserved_both",
            "raw_status": "unresolved_preserved_both",
            "status_code": "unresolved_conflict",
        }

    return {
        "id": record.get("id"),
        "type": "Program",
        "name": record.get("name"),
        "attributes": attributes,
        "missing_fields": missing_fields,
        "status": status,
        "provenance": provenance,
        "badges": badges,
        "conflict": conflict,
    }


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


@router.get("/programs")
async def programs(
    level: str | None = Query(None, description="Filter by level: UG, PG, or Research"),
    q: str | None = Query(None, description="Search query"),
    limit: int = Query(100, ge=1, le=500, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset"),
):
    """Program directory with level filter."""
    settings = get_cached_settings()

    # Validate level
    if level is not None and level not in _VALID_LEVELS:
        return error_response(
            422, INVALID_PARAMETER,
            f"Invalid value for parameter 'level'. Must be one of: {', '.join(sorted(_VALID_LEVELS))}.",
            details={"parameter": "level"},
        )

    if not _db_available():
        return error_response(503, DATABASE_UNAVAILABLE, "Neo4j is unavailable.")

    db = settings.neo4j_database
    timeout = settings.infonet_query_timeout_s

    try:
        if not _data_loaded(db, timeout):
            return error_response(503, DATA_NOT_LOADED, "No INFONET data loaded.")

        cypher = (
            "MATCH (pr:InfonetManaged:Entity:Program) "
            "RETURN pr.id AS id, pr.name AS name, "
            "pr.level AS level, pr.intake AS intake, "
            "pr.intake_count AS intake_count, pr.duration AS duration, "
            "pr.department_id AS department_id, "
            "pr.conflict_group AS conflict_group, "
            "pr.extraction_method AS extraction_method, "
            "pr.extraction_status AS extraction_status, "
            "pr.department_link_status AS department_link_status, "
            "pr.source_url AS source_url, "
            "pr.source_section AS source_section, "
            "pr.source_evidence AS source_evidence, "
            "pr.content_hash AS content_hash"
        )

        params: dict[str, Any] = {}
        if level is not None:
            cypher = cypher.replace(
                "RETURN",
                "WHERE pr.level = $level RETURN",
            )
            params["level"] = level

        rows = execute_read_query(cypher, parameters=params, database=db, timeout=timeout)

        search_query = None
        if q is not None:
            search_query = q.strip()
            if not search_query:
                search_query = None

        matched: list[tuple[bool, str, str, dict[str, Any]]] = []
        for row in rows:
            name = row.get("name") or ""
            name_lower = name.lower()
            if search_query:
                matches, contiguous = _search_matches(name_lower, search_query)
                if not matches:
                    continue
                matched.append((not contiguous, name_lower, row.get("id", ""), row))
            else:
                matched.append((False, name_lower, row.get("id", ""), row))

        matched.sort(key=lambda x: (x[0], x[1], x[2]))

        total = len(matched)
        page = matched[offset : offset + limit]
        items = [_build_program_item(row) for _, _, _, row in page]

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "facets": {},
        }

    except (ServiceUnavailable, Neo4jError) as exc:
        logger.warning("Programs query failed: %s", exc.__class__.__name__)
        return error_response(503, DATABASE_UNAVAILABLE, "Database query failed.")
