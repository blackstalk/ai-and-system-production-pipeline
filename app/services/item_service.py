"""Business logic for items — the layer AI code review scrutinizes most.

Transport-agnostic on purpose: no FastAPI imports here. This is where
"business logic" findings (incorrect assumptions, bad state transitions,
missing validation) actually live, as opposed to formatting or typing
issues that deterministic tooling already covers.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.errors import InvalidItemError
from app.core.logging import get_logger, log_with_fields
from app.models.item import Item, ItemCreate, ItemList
from app.repositories.item_repository import ItemRepository

logger = get_logger(__name__)


class ItemService:
    def __init__(self, repository: ItemRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    def create_item(self, payload: ItemCreate) -> Item:
        item = Item(
            name=payload.name,
            description=payload.description,
            price_cents=payload.price_cents,
            quantity=payload.quantity,
        )
        created = self._repository.add(item)
        log_with_fields(
            logger,
            20,
            "item created",
            item_id=created.id,
            price_cents=created.price_cents,
        )
        return created

    def get_item(self, item_id: str) -> Item:
        return self._repository.get(item_id)

    def list_items(self, limit: int, offset: int) -> ItemList:
        if limit <= 0 or limit > self._settings.max_items_page_size:
            raise InvalidItemError(
                f"limit must be between 1 and {self._settings.max_items_page_size}"
            )
        if offset < 0:
            raise InvalidItemError("offset must be non-negative")

        items, total = self._repository.list(limit=limit, offset=offset)
        return ItemList(items=items, total=total)

    def delete_item(self, item_id: str) -> None:
        self._repository.delete(item_id)
        log_with_fields(logger, 20, "item deleted", item_id=item_id)
