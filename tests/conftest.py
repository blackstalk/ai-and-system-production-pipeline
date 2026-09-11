from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import reset_state_for_tests
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    reset_state_for_tests()
    with TestClient(app) as test_client:
        yield test_client
    reset_state_for_tests()
