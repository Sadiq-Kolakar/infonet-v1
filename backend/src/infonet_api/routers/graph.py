"""
GET /api/v1/graph

Returns the complete eligible graph in a Cytoscape-friendly format.
Only includes :InfonetManaged:Entity nodes and approved relationship types:
AFFILIATED_WITH, HAS_LABORATORY, OFFERS_PROGRAM, IS_HOD_OF.
Auxiliary nodes (HodClaim, ProgramConflict, PipelineRun) are strictly excluded.
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
from infonet_common.catalogue import ENTITY_TYPES, RELATIONSHIP_TYPES
from infonet_common.status_mapping import (
    DISPLAY_CODE_NOT_RECORDED,
    DISPLAY_CODE_USER_CONFIRMED_ASSERTION,
    format_iso_date,
    map_entity_display_code,
    map_relationship_display_code,
)

logger = logging.getLogger("infonet_api.routers.graph")

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


@router.get("/graph")
async def get_graph():
    """Whole graph in Cytoscape format."""
    settings = get_cached_settings()

    if not _db_available():
        return error_response(503, DATABASE_UNAVAILABLE, "Neo4j is unavailable.")

    try:
        db = settings.neo4j_database
        timeout = settings.infonet_query_timeout_s

        if not _data_loaded(db, timeout):
            return error_response(503, DATA_NOT_LOADED, "No INFONET data loaded.")

        # 1. Fetch all managed entity nodes
        node_rows = execute_read_query(
            "MATCH (n:InfonetManaged:Entity) "
            "RETURN n.id AS id, n.name AS name, labels(n) AS labels, "
            "       n.extraction_status AS extraction_status "
            "ORDER BY n.name, n.id",
            database=db,
            timeout=timeout,
        )

        nodes: list[dict[str, Any]] = []
        for r in node_rows:
            nid = r["id"]
            name = r.get("name")
            labels = r.get("labels", [])
            ext_status = r.get("extraction_status")

            entity_type = "Entity"
            for label in labels:
                if label in ENTITY_TYPES:
                    entity_type = label
                    break

            if entity_type == "Department":
                status_codes = [DISPLAY_CODE_NOT_RECORDED]
            else:
                status_codes = [map_entity_display_code(ext_status)]

            nodes.append({
                "data": {
                    "id": nid,
                    "label": name or nid,
                    "type": entity_type,
                    "status_codes": status_codes,
                }
            })

        # 2. Fetch all approved edges where both endpoints are InfonetManaged Entity nodes
        edge_rows = execute_read_query(
            "MATCH (a:InfonetManaged:Entity)-[r]->(b:InfonetManaged:Entity) "
            "WHERE type(r) IN ['AFFILIATED_WITH','HAS_LABORATORY','OFFERS_PROGRAM','IS_HOD_OF'] "
            "RETURN a.id AS source, b.id AS target, type(r) AS rel_type, "
            "       properties(r) AS rel_props "
            "ORDER BY a.id, b.id, type(r)",
            database=db,
            timeout=timeout,
        )

        edges: list[dict[str, Any]] = []
        found_rel_types: set[str] = set()

        for r in edge_rows:
            source = r["source"]
            target = r["target"]
            rtype = r["rel_type"]
            rprops = r.get("rel_props", {})
            found_rel_types.add(rtype)

            if rtype == "IS_HOD_OF" or rprops.get("confirmation_source") == "user_confirmed":
                edge_id = rprops.get("id") or f"OVERRIDE-IS-HOD-OF-{source}-{target}"
                raw_status = rprops.get("raw_status", "user_confirmed_project_override")
                status_code = DISPLAY_CODE_USER_CONFIRMED_ASSERTION
                conf_source = "user_confirmed"
                conf_on = format_iso_date(rprops.get("confirmed_on")) or "2026-10-26"
                indep_verified = False
            else:
                edge_id = rprops.get("id") or f"REL-{rtype}-{source}-{target}"
                raw_status = rprops.get("confidence_status", "inferred_from_cse_department_page_needs_review")
                status_code = map_relationship_display_code(rprops.get("confidence_status"))
                conf_source = rprops.get("confirmation_source")
                conf_on = format_iso_date(rprops.get("confirmed_on"))
                indep_verified = bool(rprops.get("independent_source_verified", False))

            edges.append({
                "data": {
                    "id": edge_id,
                    "source": source,
                    "target": target,
                    "type": rtype,
                    "raw_status": raw_status,
                    "status_code": status_code,
                    "confirmation_source": conf_source,
                    "confirmed_on": conf_on,
                    "independent_source_verified": indep_verified,
                    "source_url": rprops.get("source_url"),
                }
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "meta": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "relationship_types": sorted(found_rel_types),
            },
        }

    except (ServiceUnavailable, Neo4jError) as exc:
        logger.warning("Graph query failed: %s", exc.__class__.__name__)
        return error_response(503, DATABASE_UNAVAILABLE, "Database query failed.")
