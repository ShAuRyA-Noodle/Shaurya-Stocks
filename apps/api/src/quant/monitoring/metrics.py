"""
Prometheus metrics + HTTP middleware.

`/metrics` exposes the standard text format. The middleware records:
- request count, labeled by method/path/status
- request latency histogram
- in-flight gauge

We use a path template (from the matched route) so `/orders/{uuid}` collapses
into a single bucket instead of exploding cardinality.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.responses import Response as StarletteResponse

REGISTRY = CollectorRegistry(auto_describe=True)

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests processed.",
    labelnames=("method", "path", "status"),
    registry=REGISTRY,
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    labelnames=("method", "path"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)
IN_FLIGHT = Gauge(
    "http_requests_in_flight",
    "Current number of requests being served.",
    registry=REGISTRY,
)

# Trading-specific metrics. These are incremented from the OrderService etc.
ORDERS_SUBMITTED = Counter(
    "orders_submitted_total",
    "Orders submitted to broker (after risk check passed).",
    labelnames=("side", "symbol"),
    registry=REGISTRY,
)
ORDERS_REJECTED = Counter(
    "orders_rejected_total",
    "Orders rejected before reaching broker.",
    labelnames=("reason",),
    registry=REGISTRY,
)
KILL_SWITCH_STATE = Gauge(
    "kill_switch_engaged",
    "1 if the global kill switch is engaged, 0 otherwise.",
    registry=REGISTRY,
)


def _route_template(request: Request) -> str:
    """Use the matched route's path template so dynamic segments collapse."""
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    start = time.perf_counter()
    IN_FLIGHT.inc()
    try:
        response = await call_next(request)
    except Exception:
        path = _route_template(request)
        REQUESTS.labels(request.method, path, "500").inc()
        LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
        IN_FLIGHT.dec()
        raise

    path = _route_template(request)
    REQUESTS.labels(request.method, path, str(response.status_code)).inc()
    LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
    IN_FLIGHT.dec()
    return response


def metrics_endpoint() -> StarletteResponse:
    data = generate_latest(REGISTRY)
    return StarletteResponse(content=data, media_type=CONTENT_TYPE_LATEST)


def install_metrics(app: FastAPI) -> None:
    app.middleware("http")(metrics_middleware)
    app.get("/metrics", tags=["meta"], include_in_schema=False)(metrics_endpoint)
