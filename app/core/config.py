"""Application configuration sourced from environment variables.

Kept intentionally minimal: a real deployment would layer this with a
secrets manager (AWS Secrets Manager, Vault, etc.) rather than raw env
vars, but the interface below would not need to change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_name: str = "ai-production-pipeline"
    environment: str = "development"
    log_level: str = "INFO"
    max_items_page_size: int = 100
    deployment_track: str = "stable"  # "stable" or "canary" — see docs/deployment-strategy.md


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "ai-production-pipeline"),
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        max_items_page_size=int(os.getenv("MAX_ITEMS_PAGE_SIZE", "100")),
        deployment_track=os.getenv("DEPLOYMENT_TRACK", "stable"),
    )
