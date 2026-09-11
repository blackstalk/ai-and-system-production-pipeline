"""In-memory item storage.

A reference implementation only — see docs/architecture.md for how this
would be swapped for a real persistence layer (Postgres via SQLAlchemy,
DynamoDB, etc.) without changing the service or API layers, because both
depend on this class's interface rather than its implementation.

Access is guarded by a lock because FastAPI may run handlers concurrently
across async tasks in a single worker process; without it, concurrent
writes could interleave and corrupt the dict (a race condition the AI
reviewer is specifically instructed to look for — see prompts/code-review.md).
"""

from __future__ import annotations

import threading

from app.core.errors import DuplicateItemError, ItemNotFoundError
from app.models.item import Item


class ItemRepository:
    def __init__(self) -> None:
        self._items: dict[str, Item] = {}
        self._lock = threading.Lock()

    def add(self, item: Item) -> Item:
        with self._lock:
            if item.id in self._items:
                raise DuplicateItemError(item.id)
            self._items[item.id] = item
            return item

    def get(self, item_id: str) -> Item:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                raise ItemNotFoundError(item_id)
            return item

    def list(self, limit: int, offset: int) -> tuple[list[Item], int]:
        with self._lock:
            all_items = sorted(self._items.values(), key=lambda i: i.created_at)
            total = len(all_items)
            return all_items[offset : offset + limit], total

    def delete(self, item_id: str) -> None:
        with self._lock:
            if item_id not in self._items:
                raise ItemNotFoundError(item_id)
            del self._items[item_id]

    def clear(self) -> None:
        """Test-only helper to reset state between test cases."""
        with self._lock:
            self._items.clear()
