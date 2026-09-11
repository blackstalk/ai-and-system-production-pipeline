"""Item resource endpoints.

Error translation happens once, here, at the boundary: domain errors
raised by the service layer are mapped to HTTP status codes so the
service layer never has to know about HTTP semantics.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_item_service
from app.core.errors import InvalidItemError, ItemNotFoundError
from app.models.item import Item, ItemCreate, ItemList
from app.services.item_service import ItemService

router = APIRouter(prefix="/api/items", tags=["items"])

ServiceDep = Annotated[ItemService, Depends(get_item_service)]


@router.get("", response_model=ItemList)
def list_items(
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ItemList:
    try:
        return service.list_items(limit=limit, offset=offset)
    except InvalidItemError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, service: ServiceDep) -> Item:
    return service.create_item(payload)


@router.get("/{item_id}", response_model=Item)
def get_item(item_id: str, service: ServiceDep) -> Item:
    try:
        return service.get_item(item_id)
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: str, service: ServiceDep) -> None:
    try:
        service.delete_item(item_id)
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
