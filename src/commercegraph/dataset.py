"""Strict source validation, performed before NetworkX can create endpoint nodes."""

import hashlib
from datetime import date
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

Money = Annotated[StrictInt, Field(ge=0)]
Quantity = Annotated[StrictInt, Field(gt=0)]
Identifier = Annotated[str, Field(min_length=1, pattern=r"^[A-Z][0-9]{2,}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NamedEntity(StrictModel):
    id: Identifier
    name: Annotated[str, Field(min_length=1)]


class Product(NamedEntity):
    brand_id: Identifier
    category_id: Identifier
    price_paise: Money


class Order(StrictModel):
    id: Identifier
    customer_id: Identifier
    date: date
    status: Literal["delivered", "pending", "cancelled"]

    @field_validator("date", mode="before")
    @classmethod
    def require_iso_date(cls, value):
        if isinstance(value, date):
            return value
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError("Date must be an ISO YYYY-MM-DD string")
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError("Date must use canonical YYYY-MM-DD format")
        return parsed


class OrderItem(StrictModel):
    id: Identifier
    order_id: Identifier
    product_id: Identifier
    quantity: Quantity
    unit_price_paise: Money


class Supply(StrictModel):
    vendor_id: Identifier
    product_id: Identifier


class Marker(StrictModel):
    id: Identifier
    value: str
    product_id: Identifier


class Dataset(StrictModel):
    schema_version: Annotated[StrictInt, Field(ge=1, le=1)]
    currency: Literal["INR"]
    brands: list[NamedEntity]
    categories: list[NamedEntity]
    vendors: list[NamedEntity]
    customers: list[NamedEntity]
    products: list[Product]
    supplies: list[Supply]
    orders: list[Order]
    order_items: list[OrderItem]
    markers: list[Marker]

    @model_validator(mode="after")
    def check_references(self):
        collections = {
            name: getattr(self, name)
            for name in (
                "brands",
                "categories",
                "vendors",
                "customers",
                "products",
                "orders",
                "order_items",
                "markers",
            )
        }
        ids = {}
        for name, records in collections.items():
            ids[name] = {record.id for record in records}
            if len(ids[name]) != len(records):
                raise ValueError(f"Duplicate IDs in {name}")
        references = {
            "brand_id": "brands",
            "category_id": "categories",
            "vendor_id": "vendors",
            "customer_id": "customers",
            "product_id": "products",
            "order_id": "orders",
        }
        for records in [*collections.values(), self.supplies]:
            for record in records:
                for field, target in references.items():
                    if hasattr(record, field) and getattr(record, field) not in ids[target]:
                        raise ValueError(f"Missing {target} reference: {getattr(record, field)}")
        pairs = {(r.vendor_id, r.product_id) for r in self.supplies}
        if len(pairs) != len(self.supplies):
            raise ValueError("Duplicate supply pairs")
        with_items = {item.order_id for item in self.order_items}
        if ids["orders"] - with_items:
            raise ValueError("Every order must have at least one item")
        return self


def load_dataset(path: str | Path | None = None) -> tuple[Dataset, str]:
    raw = (
        Path(path).read_bytes()
        if path
        else files("commercegraph").joinpath("data/ecommerce.json").read_bytes()
    )
    return Dataset.model_validate_json(raw), hashlib.sha256(raw).hexdigest()
