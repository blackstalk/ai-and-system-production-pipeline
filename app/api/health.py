"""Liveness and readiness endpoints.

Kept distinct on purpose: /health answers "is the process alive" (used
by an orchestrator to decide whether to restart the container), while
/ready answers "can this instance safely receive traffic" (used by a
load balancer / canary controller before routing requests to it). See
docs/deployment-strategy.md.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ready", "deployment_track": settings.deployment_track}
