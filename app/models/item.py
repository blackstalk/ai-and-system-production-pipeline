"""Pydantic schemas for the Item resource.

Validation lives here at the API boundary (pydantic constraints) so the
service layer can assume inputs are already well-formed by the time it
receives them — this is the "validate at the boundary" pattern called
out in docs/threat-model.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    price_cents: int = Field(
        gt=0, le=100_000_000, description="Price in integer cents; avoids float rounding bugs"
    )
    quantity: int = Field(ge=0, le=1_000_000)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank or whitespace-only")
        return stripped


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str | None = None
    price_cents: int
    quantity: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ItemList(BaseModel):
    items: list[Item]
    total: int
