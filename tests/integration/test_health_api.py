from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_deployment_track(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert "deployment_track" in body


def test_metrics_exposes_prometheus_format(client: TestClient) -> None:
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_responses_include_request_id_header(client: TestClient) -> None:
    response = client.get("/health")

    assert "x-request-id" in response.headers


def test_incoming_request_id_is_propagated(client: TestClient) -> None:
    response = client.get("/health", headers={"x-request-id": "test-correlation-123"})

    assert response.headers["x-request-id"] == "test-correlation-123"
