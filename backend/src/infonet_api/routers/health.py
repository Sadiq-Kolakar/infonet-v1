"""
GET /api/v1/health

Returns HTTP 200 with a JSON body reporting API liveness, Neo4j
connectivity, and whether usable data is loaded.  This is the sole
endpoint exempt from the 503 dependency-error pattern — scripts and the
frontend read the body to determine the actual state.

No credentials, connection strings, stack traces, or internal host
details are exposed.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from infonet_api.config import get_cached_settings
from infonet_api.db.neo4j import get_driver

logger = logging.getLogger("infonet_api.routers.health")

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """
    Health probe — always HTTP 200.

    Body fields:
      api           – "up" (always, if the process is alive)
      database      – "up" | "down"
      data_loaded   – true | false
    """
    settings = get_cached_settings()
    db_status = "down"
    data_loaded = False

    driver = get_driver()
    if driver is not None:
        try:
            driver.verify_connectivity()
            db_status = "up"
        except (ServiceUnavailable, Neo4jError) as exc:
            logger.warning(
                "Health check — database unreachable: %s", exc.__class__.__name__
            )

    # If the database is up, check whether usable entity data exists.
    if db_status == "up" and driver is not None:
        try:
            with driver.session(database=settings.neo4j_database) as session:
                result = session.execute_read(
                    lambda tx: tx.run(
                        "MATCH (n:InfonetManaged:Entity) "
                        "RETURN count(n) AS cnt",
                        timeout=settings.infonet_query_timeout_s,
                    ).single()
                )
                if result and result["cnt"] > 0:
                    data_loaded = True
        except (ServiceUnavailable, Neo4jError) as exc:
            logger.warning(
                "Health check — data probe failed: %s", exc.__class__.__name__
            )
            # Database *was* reachable for verify_connectivity but the
            # query failed — keep db_status = "up", data_loaded = False.

    return {
        "api": "up",
        "database": db_status,
        "data_loaded": data_loaded,
    }
