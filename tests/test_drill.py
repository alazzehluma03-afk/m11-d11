"""YOUR self-tests for the toy-service instrumentation.

Per the drill guide, write at least 4 substantive test functions, each with at
least one `assert`. The autograder enforces the structure via AST
(`test_learner_self_test_exists_and_passes`).

Required coverage:
  1. After 3 calls to POST /echo and 2 calls to GET /sum, GET /metrics returns 200.
  2. The /metrics body contains the three metric names.
  3. The /metrics body contains a line for requests_total{path="/echo",status="200"} with value >= 3.
  4. Every non-/metrics response has an X-Request-ID response header that is non-empty.
"""

import pytest
import re

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_metrics_endpoint_returns_200_after_traffic():
    """GET /metrics returns 200 after 3 calls to /echo and 2 calls to /sum."""
    # import app from your module, use FastAPI's TestClient to issue the
    # 5 calls, then GET /metrics and assert status_code == 200.

    for _ in range(3):
        client.post(
            "/echo",
            json={"message": "hello"},
        )

    for _ in range(2):
        client.get(
            "/sum",
            params={"a": 1, "b": 2},
        )

    response = client.get("/metrics")

    assert response.status_code == 200

def test_metrics_body_contains_three_metric_families():
    """The /metrics body contains requests_total, request_latency_seconds, inflight_requests."""
    #  GET /metrics and assert all three metric names are substrings of resp.text.
    
    response = client.get("/metrics")
    body = response.text
    assert "requests_total" in body
    assert "request_latency_seconds" in body
    assert "inflight_requests" in body  


def test_echo_counter_has_expected_value():
    """After 3 calls to /echo, requests_total{path="/echo",status="200"} >= 3."""
    # issue 3 POST /echo calls, GET /metrics, parse with a regex, assert >= 3.

    for _ in range(3):
        client.post(
            "/echo",
            json={"message": "hello"},
        )

    response = client.get("/metrics")

    match = re.search(
        r'requests_total\{path="/echo",status="200"\} (\d+(\.\d+)?)',
        response.text,
    )

    assert match is not None
    assert float(match.group(1)) >= 3


def test_x_request_id_header_set_on_every_non_metrics_response():
    """Every non-/metrics response carries a non-empty X-Request-ID header."""
    #  call /echo and /sum, assert response.headers["X-Request-ID"] is set
    # and non-empty for each.

    echo_response = client.post(
        "/echo",
        json={"message": "hello"},
    )

    sum_response = client.get(
        "/sum",
        params={"a": 1, "b": 2},
    )

    assert "X-Request-ID" in echo_response.headers
    assert echo_response.headers["X-Request-ID"] != ""

    assert "X-Request-ID" in sum_response.headers
    assert sum_response.headers["X-Request-ID"] != ""