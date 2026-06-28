"""Toy FastAPI service for the Module 11 Core Skills Drill.

Two endpoints (POST /echo, GET /sum) on an in-memory app. Your job:

  1. Declare three Prometheus metrics at module scope (requests_total,
     request_latency_seconds, inflight_requests).
  2. Implement three ASGI middlewares (RequestId, StructuredLogging, Metrics)
     and add them to the app in the correct order.
  3. Mount /metrics via prometheus_client.make_asgi_app().

The published Drill page is the canonical task list. The autograder verifies
the metrics surface, header behavior, and a JSON log line is emitted.
"""

# import Counter, Gauge, Histogram, make_asgi_app from prometheus_client.

#  import uuid, json, logging, time, contextvars as you need them.
from fastapi import FastAPI, Request
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    make_asgi_app,
)

import uuid
import json
import logging
import time
import contextvars

#  declare requests_total Counter (labels: path, status) at module scope.
#  declare request_latency_seconds Histogram at module scope.
#       Labels: ["path"]. Use this explicit bucket sequence
#       (do NOT use prometheus_client.Histogram's DEFAULT_BUCKETS --
#       the published Drill guide pins these exact values):
#         buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
#  declare inflight_requests Gauge (no labels) at module scope.
requests_total = Counter(
    "requests_total",
    "Total HTTP requests",
    ["path", "status"],
)

request_latency_seconds = Histogram(
    "request_latency_seconds",
    "Request latency in seconds",
    ["path"],
    buckets=[
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1,
        2.5,
        5,
        10,
    ],
)

inflight_requests = Gauge(
    "inflight_requests",
    "In-flight requests",
)

# declare a module-level ContextVar named request_id_var (default "").
request_id_var = contextvars.ContextVar(
    "request_id_var",
    default="",
)

#  implement RequestIdMiddleware.
#   - On entry: generate uuid4().hex and store it in request_id_var.
#   - On response: set the X-Request-ID header.
class RequestIdMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex
        request_id_var.set(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    

#  implement StructuredLoggingMiddleware.
#   - Time the request.
#   - Emit one JSON line at INFO level via the logging module with keys:
#     ts, level, request_id, path, status, latency_ms.
#   - Do NOT use print(...).
class StructuredLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        start = time.time()

        response = await call_next(request)

        latency_ms = (time.time() - start) * 1000

        log_data = {
            "ts": time.time(),
            "level": "INFO",
            "request_id": request_id_var.get(),
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": latency_ms,
        }

        logging.getLogger("app").info(json.dumps(log_data))

        return response

#  implement MetricsMiddleware.
#   - On entry: increment inflight_requests.
#   - Time the handler.
#   - On exit (try/finally): decrement inflight_requests, increment
#     requests_total.labels(path=..., status=...).inc(),
#     call request_latency_seconds.labels(path=...).observe(elapsed).

class MetricsMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/metrics"):
         return await call_next(request)
        
        inflight_requests.inc()
        start = time.time()

        try:
            response = await call_next(request)
        finally:
            inflight_requests.dec()

        elapsed = time.time() - start

        requests_total.labels(
            path=request.url.path,
            status=str(response.status_code),
        ).inc()

        request_latency_seconds.labels(
            path=request.url.path,
        ).observe(elapsed)

        return response
    
class EchoRequest(BaseModel):
    message: str


app = FastAPI(title="M11 Drill — Toy FastAPI Service")


#  wire the three middlewares onto `app` in the correct order.
#       Last add_middleware is outermost (request-id outer, metrics inner).
app.add_middleware(RequestIdMiddleware)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(MetricsMiddleware)

#  mount /metrics on `app` using make_asgi_app().
app.mount("/metrics", make_asgi_app())

# ---------------------------------------------------------------------------
# Endpoints (do not modify — these are what the autograder hits with traffic).
# ---------------------------------------------------------------------------


@app.post("/echo")
def echo(req: EchoRequest):
    return {"echo": req.message}


@app.get("/sum")
def sum_endpoint(a: int = 0, b: int = 0):
    return {"sum": a + b}
