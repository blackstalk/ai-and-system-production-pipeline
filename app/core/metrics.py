"""Prometheus-style metrics for the request/error/duration golden signals.

Exposed at GET /metrics in the standard Prometheus text exposition
format. See docs/deployment-strategy.md for how these feed canary
promotion/rollback decisions.
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
    registry=REGISTRY,
)

REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    registry=REGISTRY,
)

ERROR_COUNT = Counter(
    "http_errors_total",
    "Total HTTP requests that resulted in a 5xx response",
    ["method", "path", "status_code"],
    registry=REGISTRY,
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
