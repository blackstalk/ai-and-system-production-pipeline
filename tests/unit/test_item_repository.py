from __future__ import annotations

import threading

import pytest

from app.core.errors import DuplicateItemError, ItemNotFoundError
from app.models.item import Item
from app.repositories.item_repository import ItemRepository


def make_item(**overrides: object) -> Item:
    defaults: dict[str, object] = {"name": "Widget", "price_cents": 100, "quantity": 1}
    defaults.update(overrides)
    return Item(**defaults)  # type: ignore[arg-type]


def test_add_then_get_round_trips() -> None:
    repo = ItemRepository()
    item = make_item()

    repo.add(item)

    assert repo.get(item.id) == item


def test_add_duplicate_id_raises() -> None:
    repo = ItemRepository()
    item = make_item()
    repo.add(item)

    with pytest.raises(DuplicateItemError):
        repo.add(item)


def test_get_missing_raises_not_found() -> None:
    repo = ItemRepository()

    with pytest.raises(ItemNotFoundError):
        repo.get("missing")


def test_delete_missing_raises_not_found() -> None:
    repo = ItemRepository()

    with pytest.raises(ItemNotFoundError):
        repo.delete("missing")


def test_concurrent_adds_do_not_lose_writes() -> None:
    """Regression guard for the race condition class AI review is asked to flag."""
    repo = ItemRepository()
    items = [make_item(name=f"item-{i}") for i in range(50)]

    threads = [threading.Thread(target=repo.add, args=(item,)) for item in items]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    stored, total = repo.list(limit=100, offset=0)
    assert total == 50
    assert len(stored) == 50
