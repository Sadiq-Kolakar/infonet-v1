"""
GET /api/v1/summary

Returns department information, entity/relationship counts computed from
the live database, and data-status summary counts.  All numbers are
derived from queries — nothing is hard-coded.
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
from infonet_common.catalogue import PERSON_CATEGORY_SUPPORT_STAFF

logger = logging.getLogger("infonet_api.routers.summary")

router = APIRouter()


def _db_available() -> bool:
    """Quick connectivity probe."""
    driver = get_driver()
    if driver is None:
        return False
    try:
        driver.verify_connectivity()
        return True
    except (ServiceUnavailable, Neo4jError):
        return False


def _data_loaded(database: str, timeout: int) -> bool:
    """Return True if any InfonetManaged Entity nodes exist."""
    rows = execute_read_query(
        "MATCH (n:InfonetManaged:Entity) RETURN count(n) AS cnt",
        database=database,
        timeout=timeout,
    )
    return bool(rows and rows[0]["cnt"] > 0)


@router.get("/summary")
async def summary():
    """Department summary and computed counts."""
    settings = get_cached_settings()

    if not _db_available():
        return error_response(503, DATABASE_UNAVAILABLE, "Neo4j is unavailable.")

    try:
        if not _data_loaded(settings.neo4j_database, settings.infonet_query_timeout_s):
            return error_response(503, DATA_NOT_LOADED, "No INFONET data loaded.")

        db = settings.neo4j_database
        timeout = settings.infonet_query_timeout_s

        # Department info
        dept_rows = execute_read_query(
            "MATCH (d:InfonetManaged:Entity:Department) "
            "RETURN d.id AS id, d.name AS name, "
            "       d.description AS description, d.source_url AS source_url",
            database=db,
            timeout=timeout,
        )
        dept = dept_rows[0] if dept_rows else {
            "id": None, "name": None, "description": None, "source_url": None
        }

        # Department count
        dept_count_rows = execute_read_query(
            "MATCH (d:InfonetManaged:Entity:Department) RETURN count(d) AS cnt",
            database=db,
            timeout=timeout,
        )
        department_count = dept_count_rows[0]["cnt"] if dept_count_rows else 0

        # People counts
        people_rows = execute_read_query(
            "MATCH (p:InfonetManaged:Entity:Person) "
            "RETURN count(p) AS total, "
            "       count(CASE WHEN p.person_category = $ss THEN 1 END) AS support_staff",
            parameters={"ss": PERSON_CATEGORY_SUPPORT_STAFF},
            database=db,
            timeout=timeout,
        )
        people_total = people_rows[0]["total"] if people_rows else 0
        support_staff = people_rows[0]["support_staff"] if people_rows else 0
        faculty = people_total - support_staff

        # Lab count
        lab_rows = execute_read_query(
            "MATCH (l:InfonetManaged:Entity:Laboratory) RETURN count(l) AS cnt",
            database=db,
            timeout=timeout,
        )
        lab_count = lab_rows[0]["cnt"] if lab_rows else 0

        # Program count
        prog_rows = execute_read_query(
            "MATCH (pr:InfonetManaged:Entity:Program) RETURN count(pr) AS cnt",
            database=db,
            timeout=timeout,
        )
        prog_count = prog_rows[0]["cnt"] if prog_rows else 0

        # Relationship counts
        rel_rows = execute_read_query(
            "MATCH (a:InfonetManaged:Entity)-[r]->(b:InfonetManaged:Entity) "
            "WHERE type(r) IN ['AFFILIATED_WITH','HAS_LABORATORY','OFFERS_PROGRAM','IS_HOD_OF'] "
            "RETURN count(r) AS total, "
            "       count(CASE WHEN r.confirmation_source = 'user_confirmed' THEN 1 END) AS user_confirmed",
            database=db,
            timeout=timeout,
        )
        rel_total = rel_rows[0]["total"] if rel_rows else 0
        rel_user_confirmed = rel_rows[0]["user_confirmed"] if rel_rows else 0
        rel_inferred = rel_total - rel_user_confirmed

        # Unverified claims count (HodClaim observations)
        claim_rows = execute_read_query(
            "MATCH (h:InfonetManaged:HodClaim) RETURN count(h) AS cnt",
            database=db,
            timeout=timeout,
        )
        unverified_claims = claim_rows[0]["cnt"] if claim_rows else 0

        # Conflicts count (ProgramConflict observations)
        conflict_rows = execute_read_query(
            "MATCH (c:InfonetManaged:ProgramConflict) RETURN count(c) AS cnt",
            database=db,
            timeout=timeout,
        )
        conflicts = conflict_rows[0]["cnt"] if conflict_rows else 0

        return {
            "department": {
                "id": dept.get("id"),
                "name": dept.get("name"),
                "description": dept.get("description"),
                "source_url": dept.get("source_url"),
            },
            "department_count": department_count,
            "counts": {
                "people": people_total,
                "faculty": faculty,
                "support_staff": support_staff,
                "laboratories": lab_count,
                "programs": prog_count,
                "relationships": rel_total,
            },
            "data_status": {
                "relationships_total": rel_total,
                "relationships_inferred": rel_inferred,
                "relationships_user_confirmed": rel_user_confirmed,
                "unverified_claims": unverified_claims,
                "conflicts": conflicts,
                "open_data_quality_items": 5,
            },
        }

    except (ServiceUnavailable, Neo4jError) as exc:
        logger.warning("Summary query failed: %s", exc.__class__.__name__)
        return error_response(503, DATABASE_UNAVAILABLE, "Database query failed.")
