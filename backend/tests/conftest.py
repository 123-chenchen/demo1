from __future__ import annotations

from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def override_db() -> Callable[[object | None], object]:
    def _override(db_object: object | None = None) -> object:
        resolved_db_object = object() if db_object is None else db_object
        app.dependency_overrides[get_db] = lambda: resolved_db_object
        return resolved_db_object

    return _override
