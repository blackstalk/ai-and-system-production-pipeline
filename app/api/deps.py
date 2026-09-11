"""Shared FastAPI dependencies.

A single process-lifetime repository/service pair is used since this is
an in-memory reference implementation. A real deployment would construct
a request-scoped database session here instead (e.g. SQLAlchemy
`Session` per request) while keeping the same dependency-injection shape.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.repositories.item_repository import ItemRepository
from app.services.item_service import ItemService


@lru_cache
def get_repository() -> ItemRepository:
    return ItemRepository()


def get_item_service() -> ItemService:
    return ItemService(repository=get_repository(), settings=get_settings())


def reset_state_for_tests() -> None:
    get_repository().clear()
