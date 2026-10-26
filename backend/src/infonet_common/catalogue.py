"""
Entity and relationship allow-lists for the INFONET CSE-only MVP.

This is the single source of truth for which entity types and relationship
types the API is permitted to serve.  All query builders, response
serializers, and tests must reference these sets — never hard-code type
strings in individual route handlers.
"""

from __future__ import annotations

# ── Entity type labels (Neo4j node labels after :InfonetManaged:Entity) ──

ENTITY_TYPES: frozenset[str] = frozenset({
    "Department",
    "Person",
    "Laboratory",
    "Program",
})

# ── Approved relationship types ──
# Matches 05-Database-Design.md §3.2, including the user-confirmed IS_HOD_OF.

RELATIONSHIP_TYPES: frozenset[str] = frozenset({
    "AFFILIATED_WITH",
    "HAS_LABORATORY",
    "OFFERS_PROGRAM",
    "IS_HOD_OF",
})

# Relationship direction map: (source_label, target_label)
RELATIONSHIP_DIRECTIONS: dict[str, tuple[str, str]] = {
    "AFFILIATED_WITH":  ("Person",     "Department"),
    "HAS_LABORATORY":   ("Department", "Laboratory"),
    "OFFERS_PROGRAM":   ("Department", "Program"),
    "IS_HOD_OF":        ("Person",     "Department"),
}

# ── Person-category values used by summary counts ──

PERSON_CATEGORY_SUPPORT_STAFF = "Support Staff"
