"""Domain error types and their mapping to HTTP responses.

Keeping domain errors separate from HTTP concerns means the service
layer never imports FastAPI, which keeps business logic testable in
isolation and reusable behind a different transport (CLI, worker, gRPC).
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all expected, handled application errors."""


class ItemNotFoundError(DomainError):
    def __init__(self, item_id: str) -> None:
        self.item_id = item_id
        super().__init__(f"Item '{item_id}' was not found")


class InvalidItemError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class DuplicateItemError(DomainError):
    def __init__(self, item_id: str) -> None:
        self.item_id = item_id
        super().__init__(f"Item '{item_id}' already exists")
