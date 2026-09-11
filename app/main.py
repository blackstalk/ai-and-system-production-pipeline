"""FastAPI application entrypoint.

Wires together the middleware stack (request correlation, structured
access logging, metrics), routers, and a global exception handler that
guarantees unhandled exceptions never leak stack traces to clients.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.items import router as items_router
from app.core.config import get_settings
from app.core.logging import (
    configure_logging,
    get_logger,
    get_request_id,
    log_with_fields,
    set_request_id,
)
from app.core.metrics import ERROR_COUNT, REQUEST_COUNT, REQUEST_DURATION_SECONDS, render_metrics

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("app.access")

app = FastAPI(
    title=settings.app_name,
    description="Reference application for the AI production delivery pipeline.",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(items_router)


@app.middleware("http")
async def observability_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    incoming_request_id = request.headers.get("x-request-id")
    request_id = set_request_id(incoming_request_id)

    route_path = request.url.path
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration = time.perf_counter() - start
        REQUEST_DURATION_SECONDS.labels(method=request.method, path=route_path).observe(duration)
        ERROR_COUNT.labels(method=request.method, path=route_path, status_code="500").inc()
        REQUEST_COUNT.labels(method=request.method, path=route_path, status_code="500").inc()
        log_with_fields(
            logger,
            40,
            "unhandled exception",
            method=request.method,
            path=route_path,
            duration_ms=round(duration * 1000, 2),
        )
        raise

    duration = time.perf_counter() - start
    REQUEST_DURATION_SECONDS.labels(method=request.method, path=route_path).observe(duration)
    REQUEST_COUNT.labels(
        method=request.method, path=route_path, status_code=str(response.status_code)
    ).inc()
    if response.status_code >= 500:
        ERROR_COUNT.labels(
            method=request.method, path=route_path, status_code=str(response.status_code)
        ).inc()

    response.headers["x-request-id"] = request_id
    log_with_fields(
        logger,
        20,
        "request completed",
        method=request.method,
        path=route_path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled exception reached top-level handler")
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error", "request_id": get_request_id()},
    )


@app.get("/metrics")
def metrics() -> Response:
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)
