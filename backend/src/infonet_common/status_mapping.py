"""
Display-status mapping for the INFONET API.

Raw status values from the pipeline and loader overrides are mapped to a
stable set of display codes.  Route handlers must use these mappings rather
than creating ad-hoc display strings.
"""

from __future__ import annotations

# ── Display codes (§3.4 of 04-API-Specification-final.md) ──

DISPLAY_CODE_SOURCE_STATED_NEEDS_REVIEW = "source_stated_needs_review"
DISPLAY_CODE_INFERRED_LINK = "inferred_link"
DISPLAY_CODE_USER_CONFIRMED_ASSERTION = "user_confirmed_assertion"
DISPLAY_CODE_UNVERIFIED_CLAIM = "unverified_claim"
DISPLAY_CODE_UNRESOLVED_CONFLICT = "unresolved_conflict"
DISPLAY_CODE_NOT_RECORDED = "not_recorded"


# ── Raw → display code mapping for entity extraction_status ──

ENTITY_STATUS_MAP: dict[str, str] = {
    "derived_from_saved_snapshot_needs_review": DISPLAY_CODE_SOURCE_STATED_NEEDS_REVIEW,
}

# ── Raw → display code mapping for relationship confidence_status ──

RELATIONSHIP_STATUS_MAP: dict[str, str] = {
    "inferred_from_cse_department_page_needs_review": DISPLAY_CODE_INFERRED_LINK,
    "user_confirmed_project_override": DISPLAY_CODE_USER_CONFIRMED_ASSERTION,
}


def map_entity_display_code(raw_extraction_status: str | None) -> str:
    """Return the display code for an entity's raw extraction_status."""
    if raw_extraction_status is None:
        return DISPLAY_CODE_NOT_RECORDED
    return ENTITY_STATUS_MAP.get(raw_extraction_status, DISPLAY_CODE_SOURCE_STATED_NEEDS_REVIEW)


def map_relationship_display_code(raw_confidence_status: str | None) -> str:
    """Return the display code for a relationship's raw confidence_status."""
    if raw_confidence_status is None:
        return DISPLAY_CODE_NOT_RECORDED
    return RELATIONSHIP_STATUS_MAP.get(raw_confidence_status, DISPLAY_CODE_INFERRED_LINK)


def format_iso_date(val: Any) -> str | None:
    """Format Neo4j Date, DateTime, datetime.date, datetime.datetime, or string to ISO 8601 YYYY-MM-DD string."""
    if val is None:
        return None
    if hasattr(val, "iso_format"):
        return val.iso_format()
    if hasattr(val, "isoformat"):
        return val.isoformat()[:10]
    s = str(val).strip()
    return s if s else None

