"""
GET /api/v1/people

Searchable, filterable, paginated people directory.
Uses the shared search semantics defined in the API specification.
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

logger = logging.getLogger("infonet_api.routers.people")

router = APIRouter()

# ── Allowed fields for Person entities ────────────────────────────────

_PERSON_ATTRIBUTES = frozenset({
    "role_title", "directory_category", "person_category",
    "resume_url", "department_id",
})

_PERSON_PROVENANCE_FIELDS = (
    "source_url", "source_section", "source_evidence",
    "content_hash", "extraction_status", "department_link_status",
)

_PERSON_ALL_EXPECTED = {
    "name", "role_title", "directory_category", "person_category",
    "resume_url", "department_id",
}


def _search_matches(name_lower: str, query_trimmed: str) -> tuple[bool, bool]:
    """
    Check if name matches the search query.
    Returns (matches, is_contiguous_match).
    """
    query_lower = query_trimmed.lower()
    tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", query_lower) if t]
    if not tokens:
        return True, False

    # Every token must be a substring of the name
    for token in tokens:
        if token not in name_lower:
            return False, False

    # Check contiguous match
    contiguous = query_lower in name_lower
    return True, contiguous


def _build_person_item(record: dict[str, Any]) -> dict[str, Any]:
    """Build a person list item from a Neo4j record."""
    name = record.get("name")
    extraction_status = record.get("extraction_status")
    display_code = map_entity_display_code(extraction_status)

    # Attributes — only allow-listed fields
    attributes: dict[str, Any] = {}
    for field in _PERSON_ATTRIBUTES:
        attributes[field] = record.get(field)

    # Missing fields
    missing_fields = [
        f for f in _PERSON_ALL_EXPECTED
        if record.get(f) is None or record.get(f) == ""
    ]

    # Provenance
    provenance: dict[str, Any] = {}
    for f in _PERSON_PROVENANCE_FIELDS:
        provenance[f] = record.get(f)

    # Status
    status = {
        "raw": {},
        "display_codes": [display_code],
    }
    if extraction_status:
        status["raw"]["extraction_status"] = extraction_status
    dept_link_status = record.get("department_link_status")
    if dept_link_status:
        status["raw"]["department_link_status"] = dept_link_status

    # Badges
    badges = [{"code": display_code}]
    if extraction_status:
        badges[0]["source_field"] = "extraction_status"
        badges[0]["raw_value"] = extraction_status

    return {
        "id": record.get("id"),
        "type": "Person",
        "name": name,
        "attributes": attributes,
        "missing_fields": missing_fields,
        "status": status,
        "provenance": provenance,
        "badges": badges,
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


@router.get("/people")
async def people(
    q: str | None = Query(None, description="Search query"),
    category: str | None = Query(None, description="Exact match on person_category"),
    role_title: str | None = Query(None, alias="role_title", description="Exact match on role_title"),
    sort: str = Query("name", description="Sort field (only 'name' supported)"),
    order: str = Query("asc", description="Sort order: asc or desc"),
    limit: int = Query(100, ge=1, le=500, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset"),
):
    """Searchable, filterable people directory."""
    settings = get_cached_settings()

    # Validate sort
    if sort != "name":
        return error_response(
            422, INVALID_PARAMETER,
            "Invalid value for parameter 'sort'. Only 'name' is supported.",
            details={"parameter": "sort"},
        )

    # Validate order
    if order not in ("asc", "desc"):
        return error_response(
            422, INVALID_PARAMETER,
            "Invalid value for parameter 'order'. Must be 'asc' or 'desc'.",
            details={"parameter": "order"},
        )

    # Check DB
    if not _db_available():
        return error_response(503, DATABASE_UNAVAILABLE, "Neo4j is unavailable.")

    db = settings.neo4j_database
    timeout = settings.infonet_query_timeout_s

    try:
        # Check data loaded
        if not _data_loaded(db, timeout):
            return error_response(503, DATA_NOT_LOADED, "No INFONET data loaded.")

        # Build Cypher query with filters
        cypher = (
            "MATCH (p:InfonetManaged:Entity:Person) "
            "RETURN p.id AS id, p.name AS name, "
            "p.role_title AS role_title, "
            "p.directory_category AS directory_category, "
            "p.person_category AS person_category, "
            "p.resume_url AS resume_url, "
            "p.department_id AS department_id, "
            "p.extraction_status AS extraction_status, "
            "p.department_link_status AS department_link_status, "
            "p.source_url AS source_url, "
            "p.source_section AS source_section, "
            "p.source_evidence AS source_evidence, "
            "p.content_hash AS content_hash"
        )

        params: dict[str, Any] = {}
        where_clauses: list[str] = []

        if category is not None:
            where_clauses.append("p.person_category = $category")
            params["category"] = category

        if role_title is not None:
            where_clauses.append("p.role_title = $role_title")
            params["role_title"] = role_title

        if where_clauses:
            cypher = cypher.replace(
                "RETURN",
                "WHERE " + " AND ".join(where_clauses) + " RETURN",
            )

        rows = execute_read_query(cypher, parameters=params, database=db, timeout=timeout)

        # Normalize q
        search_query = None
        if q is not None:
            search_query = q.strip()
            if not search_query:
                search_query = None

        # Apply search in-memory for ranking
        matched_items: list[tuple[bool, str, str, dict[str, Any]]] = []
        for row in rows:
            name = row.get("name") or ""
            name_lower = name.lower()

            if search_query:
                matches, contiguous = _search_matches(name_lower, search_query)
                if not matches:
                    continue
                # Sort key: contiguous first, then name, then id
                matched_items.append(
                    (not contiguous, name_lower, row.get("id", ""), row)
                )
            else:
                matched_items.append((False, name_lower, row.get("id", ""), row))

        # Sort
        reverse = order == "desc"
        matched_items.sort(key=lambda x: (x[0], x[1], x[2]), reverse=reverse)

        total = len(matched_items)

        # Facets — computed before pagination
        category_facets: dict[str, int] = {}
        role_facets: dict[str, int] = {}
        for _, _, _, row in matched_items:
            cat = row.get("person_category")
            if cat:
                category_facets[cat] = category_facets.get(cat, 0) + 1
            rt = row.get("role_title")
            if rt:
                role_facets[rt] = role_facets.get(rt, 0) + 1

        # Paginate
        page = matched_items[offset : offset + limit]

        items = [_build_person_item(row) for _, _, _, row in page]

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "facets": {
                "person_category": category_facets,
                "role_title": role_facets,
            },
        }

    except (ServiceUnavailable, Neo4jError) as exc:
        logger.warning("People query failed: %s", exc.__class__.__name__)
        return error_response(503, DATABASE_UNAVAILABLE, "Database query failed.")
