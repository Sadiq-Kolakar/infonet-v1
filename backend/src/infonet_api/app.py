"""
INFONET API — FastAPI application entry point.

Creates the application instance, configures lifespan hooks for the Neo4j
driver, registers error handlers, configures CORS, and mounts all routers under /api/v1.
Strictly read-only endpoints: GET only.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from infonet_api.config import get_cached_settings
from infonet_api.db.neo4j import close_driver, init_driver
from infonet_api.errors import validation_exception_handler
from infonet_api.routers import (
    about,
    data_quality,
    entities,
    graph,
    health,
    laboratories,
    people,
    programs,
    summary,
)

logger = logging.getLogger("infonet_api")


# ── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: create Neo4j driver.  Shutdown: close it."""
    settings = get_cached_settings()
    try:
        driver = init_driver(settings)
        logger.info("Neo4j driver created for %s", settings.neo4j_uri)
        # Attempt a connectivity check — log the result but don't abort.
        try:
            driver.verify_connectivity()
            logger.info("Neo4j connectivity verified.")
        except Exception as exc:
            logger.warning(
                "Neo4j not reachable at startup: %s — the health "
                "endpoint will report database=down.",
                exc.__class__.__name__,
            )
    except Exception as exc:
        logger.error(
            "Failed to create Neo4j driver: %s — health endpoint will "
            "report database=down.",
            exc.__class__.__name__,
        )

    yield

    close_driver()
    logger.info("Neo4j driver closed.")


# ── Application ───────────────────────────────────────────────────────

app = FastAPI(
    title="INFONET API",
    description="Read-only API for the INFONET CSE Knowledge Graph",
    version="0.1.0",
    lifespan=lifespan,
)


# ── CORS ──────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)


# ── Exception handlers ───────────────────────────────────────────────

app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]


# ── Request logging middleware ────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:  # type: ignore[type-arg]
    """Log one line per request: method, path, status, duration_ms."""
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ── Router registration ──────────────────────────────────────────────

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(summary.router, prefix="/api/v1", tags=["summary"])
app.include_router(about.router, prefix="/api/v1", tags=["about"])
app.include_router(people.router, prefix="/api/v1", tags=["people"])
app.include_router(laboratories.router, prefix="/api/v1", tags=["laboratories"])
app.include_router(programs.router, prefix="/api/v1", tags=["programs"])
app.include_router(entities.router, prefix="/api/v1", tags=["entities"])
app.include_router(graph.router, prefix="/api/v1", tags=["graph"])
app.include_router(data_quality.router, prefix="/api/v1", tags=["data-quality"])
