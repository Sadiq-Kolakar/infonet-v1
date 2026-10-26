"""
GET /api/v1/entities/{id}

Returns the detail envelope for any supported entity type.
All queries are scoped to :InfonetManaged:Entity.
Related entities are grouped by the approved relationship types:
AFFILIATED_WITH, HAS_LABORATORY, OFFERS_PROGRAM, IS_HOD_OF.
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
    NOT_FOUND,
    error_response,
)
from infonet_api.notes import get_notes_for_entity
from infonet_common.catalogue import ENTITY_TYPES, RELATIONSHIP_TYPES
from infonet_common.status_mapping import (
    DISPLAY_CODE_INFERRED_LINK,
    DISPLAY_CODE_NOT_RECORDED,
    DISPLAY_CODE_UNRESOLVED_CONFLICT,
    DISPLAY_CODE_UNVERIFIED_CLAIM,
    DISPLAY_CODE_USER_CONFIRMED_ASSERTION,
    format_iso_date,
    map_entity_display_code,
    map_relationship_display_code,
)

logger = logging.getLogger("infonet_api.routers.entities")

router = APIRouter()

_PERSON_EXPECTED = {
    "name", "role_title", "directory_category", "person_category",
    "resume_url", "department_id",
}
_LAB_EXPECTED = {"name", "department_id"}
_PROG_EXPECTED = {
    "name", "level", "intake", "intake_count", "duration",
    "department_id",
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


@router.get("/entities/{id}")
async def get_entity(id: str):
    """Detail view for any supported entity ID."""
    settings = get_cached_settings()

    if not _db_available():
        return error_response(503, DATABASE_UNAVAILABLE, "Neo4j is unavailable.")

    try:
        db = settings.neo4j_database
        timeout = settings.infonet_query_timeout_s

        if not _data_loaded(db, timeout):
            return error_response(503, DATA_NOT_LOADED, "No INFONET data loaded.")

        # Query node by ID with InfonetManaged and Entity labels
        node_rows = execute_read_query(
            "MATCH (n:InfonetManaged:Entity {id: $id}) "
            "RETURN properties(n) AS props, labels(n) AS labels",
            parameters={"id": id},
            database=db,
            timeout=timeout,
        )

        if not node_rows:
            return error_response(
                404, NOT_FOUND,
                f"Entity with id '{id}' was not found.",
                {"id": id},
            )

        row = node_rows[0]
        props: dict[str, Any] = row["props"]
        labels: list[str] = row["labels"]

        # Determine entity type
        entity_type = "Entity"
        for label in labels:
            if label in ENTITY_TYPES:
                entity_type = label
                break

        name = props.get("name")
        extraction_status = props.get("extraction_status")
        dept_link_status = props.get("department_link_status")

        # Entity attributes, missing_fields, absent_attributes
        attributes: dict[str, Any] = {}
        missing_fields: list[str] = []
        absent_attributes: list[str] = []

        if entity_type == "Department":
            attributes = {
                "description": props.get("description"),
                "source_url": props.get("source_url"),
            }
            display_codes = [DISPLAY_CODE_NOT_RECORDED]
            status_raw = {}
            evidence_note = "no_evidence_text_stored" if not props.get("source_evidence") else None
            provenance = {
                "source_url": props.get("source_url"),
                "source_section": None,
                "source_evidence": None,
                "evidence_note": evidence_note,
                "content_hash": props.get("content_hash"),
                "extraction_method": None,
                "extraction_status": None,
                "department_link_status": None,
            }

        elif entity_type == "Person":
            for f in ("role_title", "directory_category", "person_category", "resume_url", "department_id"):
                attributes[f] = props.get(f)
            missing_fields = [f for f in _PERSON_EXPECTED if props.get(f) is None or props.get(f) == ""]
            display_codes = [map_entity_display_code(extraction_status)]
            status_raw = {}
            if extraction_status:
                status_raw["extraction_status"] = extraction_status
            if dept_link_status:
                status_raw["department_link_status"] = dept_link_status

            evidence_note = "no_evidence_text_stored" if not props.get("source_evidence") else None
            provenance = {
                "source_url": props.get("source_url"),
                "source_section": props.get("source_section"),
                "source_evidence": props.get("source_evidence"),
                "evidence_note": evidence_note,
                "content_hash": props.get("content_hash"),
                "extraction_method": props.get("extraction_method"),
                "extraction_status": extraction_status,
                "department_link_status": dept_link_status,
            }

        elif entity_type == "Laboratory":
            attributes = {
                "department_id": props.get("department_id"),
                "extraction_method": props.get("extraction_method"),
            }
            missing_fields = [f for f in _LAB_EXPECTED if props.get(f) is None or props.get(f) == ""]
            absent_attributes = ["equipment", "location", "in_charge", "description"]
            display_codes = [map_entity_display_code(extraction_status)]
            status_raw = {}
            if extraction_status:
                status_raw["extraction_status"] = extraction_status
            if dept_link_status:
                status_raw["department_link_status"] = dept_link_status

            provenance = {
                "source_url": props.get("source_url"),
                "source_section": props.get("source_section"),
                "source_evidence": None,
                "evidence_note": "no_evidence_text_stored",
                "content_hash": props.get("content_hash"),
                "extraction_method": props.get("extraction_method"),
                "extraction_status": extraction_status,
                "department_link_status": dept_link_status,
            }

        elif entity_type == "Program":
            for f in ("level", "intake", "intake_count", "duration", "department_id", "conflict_group"):
                attributes[f] = props.get(f)
            missing_fields = [f for f in _PROG_EXPECTED if props.get(f) is None or props.get(f) == ""]
            display_codes = [map_entity_display_code(extraction_status)]
            status_raw = {}
            if extraction_status:
                status_raw["extraction_status"] = extraction_status
            if dept_link_status:
                status_raw["department_link_status"] = dept_link_status

            evidence_note = "no_evidence_text_stored" if not props.get("source_evidence") else None
            provenance = {
                "source_url": props.get("source_url"),
                "source_section": props.get("source_section"),
                "source_evidence": props.get("source_evidence"),
                "evidence_note": evidence_note,
                "content_hash": props.get("content_hash"),
                "extraction_method": props.get("extraction_method"),
                "extraction_status": extraction_status,
                "department_link_status": dept_link_status,
            }
        else:
            display_codes = [DISPLAY_CODE_NOT_RECORDED]
            status_raw = {}
            provenance = {
                "source_url": props.get("source_url"),
                "source_section": props.get("source_section"),
                "source_evidence": props.get("source_evidence"),
                "evidence_note": None,
                "content_hash": props.get("content_hash"),
                "extraction_method": props.get("extraction_method"),
                "extraction_status": extraction_status,
                "department_link_status": dept_link_status,
            }

        # ── Related entities ──────────────────────────────────────────
        rel_rows = execute_read_query(
            "MATCH (n:InfonetManaged:Entity {id: $id})-[r]-(m:InfonetManaged:Entity) "
            "WHERE type(r) IN ['AFFILIATED_WITH','HAS_LABORATORY','OFFERS_PROGRAM','IS_HOD_OF'] "
            "RETURN type(r) AS rel_type, "
            "       startNode(r).id = n.id AS is_outgoing, "
            "       m.id AS related_id, "
            "       m.name AS related_name, "
            "       [l IN labels(m) WHERE l IN ['Department','Person','Laboratory','Program']][0] AS related_type, "
            "       properties(r) AS rel_props",
            parameters={"id": id},
            database=db,
            timeout=timeout,
        )

        related: dict[str, list[dict[str, Any]]] = {
            "affiliated_with": [],
            "has_laboratory": [],
            "offers_program": [],
            "is_hod_of": [],
        }

        for rel in rel_rows:
            rtype = rel["rel_type"]
            is_outgoing = rel["is_outgoing"]
            rprops = rel.get("rel_props", {})
            direction = "outgoing" if is_outgoing else "incoming"

            if rtype == "IS_HOD_OF" or rprops.get("confirmation_source") == "user_confirmed":
                status_code = DISPLAY_CODE_USER_CONFIRMED_ASSERTION
                conf_source = "user_confirmed"
                conf_on = format_iso_date(rprops.get("confirmed_on")) or "2026-10-26"
                indep_verified = False
            else:
                status_code = map_relationship_display_code(rprops.get("confidence_status"))
                conf_source = rprops.get("confirmation_source")
                conf_on = format_iso_date(rprops.get("confirmed_on"))
                indep_verified = bool(rprops.get("independent_source_verified", False))

            item = {
                "id": rel["related_id"],
                "name": rel["related_name"],
                "type": rel["related_type"],
                "direction": direction,
                "rel_type": rtype,
                "raw_status": rprops.get("confidence_status") or rprops.get("raw_status"),
                "status_code": status_code,
                "confirmation_source": conf_source,
                "confirmed_on": conf_on,
                "independent_source_verified": indep_verified,
                "source_url": rprops.get("source_url"),
            }

            group_key = rtype.lower()
            if group_key in related:
                related[group_key].append(item)

        # ── Observations ──────────────────────────────────────────────
        observations: list[dict[str, Any]] = []

        # HodClaim observations
        if entity_type == "Person":
            claim_rows = execute_read_query(
                "MATCH (h:InfonetManaged:HodClaim) "
                "WHERE toLower(h.person_name) = toLower($name) "
                "RETURN properties(h) AS props",
                parameters={"name": name or ""},
                database=db,
                timeout=timeout,
            )
            for cr in claim_rows:
                cprops = cr["props"]
                observations.append({
                    "id": cprops.get("id"),
                    "observation_type": "HodClaim",
                    "status_code": DISPLAY_CODE_UNVERIFIED_CLAIM,
                    "raw_status": cprops.get("claim_status", "unverified_source_claim"),
                    "person_name": cprops.get("person_name"),
                    "role_title": cprops.get("role_title"),
                    "source_evidence": cprops.get("source_evidence"),
                    "claim_promoted_to_relationship": False,
                    "source_url": cprops.get("source_url"),
                })

        elif entity_type == "Department":
            claim_rows = execute_read_query(
                "MATCH (h:InfonetManaged:HodClaim) "
                "WHERE h.department_id = $id "
                "RETURN properties(h) AS props",
                parameters={"id": id},
                database=db,
                timeout=timeout,
            )
            for cr in claim_rows:
                cprops = cr["props"]
                observations.append({
                    "id": cprops.get("id"),
                    "observation_type": "HodClaim",
                    "status_code": DISPLAY_CODE_UNVERIFIED_CLAIM,
                    "raw_status": cprops.get("claim_status", "unverified_source_claim"),
                    "person_name": cprops.get("person_name"),
                    "role_title": cprops.get("role_title"),
                    "source_evidence": cprops.get("source_evidence"),
                    "claim_promoted_to_relationship": False,
                    "source_url": cprops.get("source_url"),
                })

        # ProgramConflict observations
        conflict_group = props.get("conflict_group")
        if entity_type == "Program" and conflict_group:
            conflict_rows = execute_read_query(
                "MATCH (c:InfonetManaged:ProgramConflict {id: $cg}) "
                "RETURN properties(c) AS props",
                parameters={"cg": conflict_group},
                database=db,
                timeout=timeout,
            )
            # Find members
            member_rows = execute_read_query(
                "MATCH (p:InfonetManaged:Entity:Program {conflict_group: $cg}) "
                "RETURN p.id AS id, p.level AS level, p.intake_count AS intake_count, p.duration AS duration",
                parameters={"cg": conflict_group},
                database=db,
                timeout=timeout,
            )
            members = [
                {
                    "id": m["id"],
                    "level": m.get("level"),
                    "intake_count": m.get("intake_count"),
                    "duration": m.get("duration"),
                }
                for m in member_rows
            ]

            for cr in conflict_rows:
                cprops = cr["props"]
                observations.append({
                    "id": cprops.get("id"),
                    "observation_type": "ProgramConflict",
                    "status_code": DISPLAY_CODE_UNRESOLVED_CONFLICT,
                    "raw_status": "unresolved_preserved_both",
                    "program_name": cprops.get("program_name"),
                    "conflicting_entity_ids": cprops.get("conflicting_entity_ids", []),
                    "members": members,
                })

        # ── Notes ─────────────────────────────────────────────────────
        notes = get_notes_for_entity(entity_type, name)

        return {
            "entity": {
                "id": id,
                "type": entity_type,
                "name": name,
                "attributes": attributes,
                "missing_fields": missing_fields,
                "absent_attributes": absent_attributes,
            },
            "status": {
                "raw": status_raw,
                "display_codes": display_codes,
            },
            "provenance": provenance,
            "related": related,
            "observations": observations,
            "notes": notes,
        }

    except (ServiceUnavailable, Neo4jError) as exc:
        logger.warning("Entity detail query failed: %s", exc.__class__.__name__)
        return error_response(503, DATABASE_UNAVAILABLE, "Database query failed.")
