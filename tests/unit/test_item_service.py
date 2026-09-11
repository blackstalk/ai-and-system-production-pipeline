from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.errors import InvalidItemError, ItemNotFoundError
from app.models.item import ItemCreate
from app.repositories.item_repository import ItemRepository
from app.services.item_service import ItemService


@pytest.fixture
def service() -> ItemService:
    return ItemService(repository=ItemRepository(), settings=Settings())


def test_create_item_persists_and_returns_generated_id(service: ItemService) -> None:
    item = service.create_item(ItemCreate(name="Widget", price_cents=1000, quantity=5))

    assert item.id
    assert item.name == "Widget"
    fetched = service.get_item(item.id)
    assert fetched == item


def test_get_item_raises_not_found_for_unknown_id(service: ItemService) -> None:
    with pytest.raises(ItemNotFoundError):
        service.get_item("does-not-exist")


def test_delete_item_removes_it(service: ItemService) -> None:
    item = service.create_item(ItemCreate(name="Widget", price_cents=1000, quantity=5))

    service.delete_item(item.id)

    with pytest.raises(ItemNotFoundError):
        service.get_item(item.id)


def test_delete_item_raises_not_found_when_already_deleted(service: ItemService) -> None:
    item = service.create_item(ItemCreate(name="Widget", price_cents=1000, quantity=5))
    service.delete_item(item.id)

    with pytest.raises(ItemNotFoundError):
        service.delete_item(item.id)


def test_list_items_paginates_in_creation_order(service: ItemService) -> None:
    created = [
        service.create_item(ItemCreate(name=f"Item {i}", price_cents=100, quantity=1))
        for i in range(5)
    ]

    page = service.list_items(limit=2, offset=1)

    assert page.total == 5
    assert [item.id for item in page.items] == [created[1].id, created[2].id]


def test_list_items_rejects_limit_above_max_page_size(service: ItemService) -> None:
    with pytest.raises(InvalidItemError):
        service.list_items(limit=1000, offset=0)


def test_list_items_rejects_negative_offset(service: ItemService) -> None:
    with pytest.raises(InvalidItemError):
        service.list_items(limit=10, offset=-1)


def test_create_item_rejects_blank_name() -> None:
    with pytest.raises(ValueError, match="blank"):
        ItemCreate(name="   ", price_cents=100, quantity=1)


def test_create_item_rejects_non_positive_price() -> None:
    with pytest.raises(ValueError):
        ItemCreate(name="Widget", price_cents=0, quantity=1)
