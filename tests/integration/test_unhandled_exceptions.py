"""Exercises the unhandled-exception path: the observability middleware's
except branch and the global exception handler in app/main.py.

Forces a failure via dependency override rather than a dedicated "throw an
exception" endpoint, so no extra attack surface is added to the real app
just to make this path testable.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_item_service, reset_state_for_tests
from app.main import app


class _ExplodingService:
    def list_items(self, limit: int, offset: int) -> None:
        raise RuntimeError("simulated unhandled failure")


@pytest.fixture
def exploding_client() -> Iterator[TestClient]:
    reset_state_for_tests()
    app.dependency_overrides[get_item_service] = lambda: _ExplodingService()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_item_service, None)
    reset_state_for_tests()


def test_unhandled_exception_returns_generic_500_with_request_id(
    exploding_client: TestClient,
) -> None:
    response = exploding_client.get("/api/items")

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "internal server error"
    assert "request_id" in body
    # No stack trace or exception message should leak to the client.
    assert "simulated unhandled failure" not in response.text


def test_unhandled_exception_propagates_client_supplied_request_id(
    exploding_client: TestClient,
) -> None:
    response = exploding_client.get("/api/items", headers={"x-request-id": "trace-me-123"})

    assert response.status_code == 500
    assert response.json()["request_id"] == "trace-me-123"
