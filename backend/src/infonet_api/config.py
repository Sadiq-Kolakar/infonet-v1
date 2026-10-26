"""
Application-level configuration for the FastAPI instance.

Reads validated settings and exposes them as a cached dependency so that
router code never directly instantiates Settings.
"""

from __future__ import annotations

from functools import lru_cache

from infonet_common.settings import Settings, get_settings


@lru_cache(maxsize=1)
def get_cached_settings() -> Settings:
    """Return a singleton Settings instance (cached for the process lifetime)."""
    return get_settings()
