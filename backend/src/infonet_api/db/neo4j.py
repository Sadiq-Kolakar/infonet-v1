"""
Neo4j driver lifecycle management.

One driver per process, created at startup and closed on shutdown.
All data queries use read-access transactions — the API never writes.
"""

from __future__ import annotations

import logging
from typing import Any

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import (
    AuthError,
    Neo4jError,
    ServiceUnavailable,
)

from infonet_common.settings import Settings

logger = logging.getLogger("infonet_api.db")

# Module-level singleton — set by lifespan hooks.
_driver: Driver | None = None


def init_driver(settings: Settings) -> Driver:
    """Create and store the module-level Neo4j driver."""
    global _driver
    _driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )
    return _driver


def close_driver() -> None:
    """Close the module-level driver (idempotent)."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def get_driver() -> Driver | None:
    """Return the current driver instance (may be None before init)."""
    return _driver


# ── Connectivity probe (read-only) ────────────────────────────────────

def verify_connectivity(settings: Settings) -> bool:
    """Return True if the driver can reach the database, without writing."""
    if _driver is None:
        return False
    try:
        _driver.verify_connectivity()
        return True
    except (ServiceUnavailable, AuthError, Neo4jError) as exc:
        logger.warning("Neo4j connectivity check failed: %s", exc.__class__.__name__)
        return False


# ── Generic read-query helper ─────────────────────────────────────────

def execute_read_query(
    query: str,
    parameters: dict[str, Any] | None = None,
    *,
    database: str | None = None,
    timeout: float | None = None,
) -> list[dict[str, Any]]:
    """
    Run a read-only Cypher query and return the result records as dicts.

    Raises RuntimeError if the driver is not initialised.
    Propagates Neo4j exceptions to callers (routers convert them to error
    responses).
    """
    if _driver is None:
        raise RuntimeError("Neo4j driver is not initialised")

    with _driver.session(database=database) as session:
        result = session.execute_read(
            lambda tx: list(tx.run(query, parameters or {}, timeout=timeout).data())
        )
    return result
