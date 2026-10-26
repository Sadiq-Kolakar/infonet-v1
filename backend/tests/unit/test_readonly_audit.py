"""
Read-only audit tests (T-API-16, T-API-17).

Verifies that the API registers only read-only routes and contains no write Cypher.
"""

from __future__ import annotations

from pathlib import Path
from fastapi.routing import APIRoute

from infonet_api.app import app


def test_routes_are_strictly_get():
    """All registered API routes must only accept GET (and HEAD)."""
    allowed_methods = {"GET", "HEAD"}
    for route in app.routes:
        if isinstance(route, APIRoute):
            non_allowed = route.methods - allowed_methods
            assert not non_allowed, (
                f"Route {route.path} exposes disallowed methods: {non_allowed}"
            )


def test_no_write_cypher_in_source_code():
    """Scan source files for prohibited mutating Cypher statements."""
    prohibited_patterns = [
        "CREATE ",
        "MERGE ",
        "SET ",
        "DELETE ",
        "DETACH DELETE",
        "DROP ",
        "LOAD CSV",
    ]

    src_dir = Path(__file__).resolve().parent.parent.parent / "src" / "infonet_api"
    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        # Check inside Cypher queries (ignore comments or error message strings)
        lines = content.splitlines()
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            # If line is inside a docstring or comment, skip
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            for kw in prohibited_patterns:
                # Disallow if inside Cypher quotes, e.g. "CREATE " or 'MERGE '
                if f'"{kw}' in line or f"'{kw}" in line or f' {kw}' in line:
                    # Exclude safe uses like count(CASE WHEN ...) or status codes
                    if "CASE WHEN" in line or "error" in line.lower() or "doc" in line.lower():
                        continue
                    raise AssertionError(
                        f"Prohibited write Cypher pattern '{kw}' detected in {py_file.name}:{i}: {line}"
                    )
