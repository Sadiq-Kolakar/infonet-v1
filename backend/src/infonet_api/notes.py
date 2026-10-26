"""
Project notes sidecar loader and matcher.

Reads backend/content/project_notes.json and matches notes to entities,
observations, and data-quality items.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("infonet_api.notes")

_PROJECT_NOTES_PATH = Path(__file__).resolve().parent.parent.parent / "content" / "project_notes.json"
_cached_notes: list[dict[str, Any]] | None = None


def load_project_notes() -> list[dict[str, Any]]:
    """Load project notes from the JSON sidecar file."""
    global _cached_notes
    if _cached_notes is not None:
        return _cached_notes

    if not _PROJECT_NOTES_PATH.exists():
        logger.warning("Project notes file not found at %s", _PROJECT_NOTES_PATH)
        return []

    try:
        with open(_PROJECT_NOTES_PATH, encoding="utf-8") as f:
            _cached_notes = json.load(f)
            return _cached_notes
    except Exception as exc:
        logger.warning("Failed to load project notes: %s", exc)
        return []


def get_notes_for_entity(entity_type: str, entity_name: str | None = None) -> list[dict[str, Any]]:
    """Return notes applicable to the given entity type and name."""
    notes = load_project_notes()
    applicable: list[dict[str, Any]] = []

    for note in notes:
        applies_to = note.get("applies_to", {})
        target_type = applies_to.get("entity_type")
        if target_type and target_type == entity_type:
            target_name = applies_to.get("name")
            if target_name is None or (entity_name and target_name.lower() in entity_name.lower()):
                applicable.append({
                    "id": note.get("id"),
                    "kind": note.get("kind"),
                    "origin": "project_note",
                    "text": note.get("text"),
                    "quotes": note.get("quotes", []),
                    "source_refs": note.get("source_refs", []),
                })

    return applicable
