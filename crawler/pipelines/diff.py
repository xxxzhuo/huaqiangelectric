from __future__ import annotations

import hashlib
from dataclasses import dataclass

from crawler.models.schemas import ChangeEvent, ProductRecord


TRACKED_FIELDS = ["title", "brand", "model", "price_min", "price_max", "stock", "seller_name"]


@dataclass
class ProductSnapshot:
    product_key: str
    hash_value: str


def _hash_record(record: ProductRecord) -> str:
    payload = "|".join(str(getattr(record, field)) for field in TRACKED_FIELDS)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def detect_change(previous: ProductRecord | None, current: ProductRecord) -> ChangeEvent:
    if previous is None:
        return ChangeEvent(product_key=current.site_product_id, change_type="new")

    changed_fields = [field for field in TRACKED_FIELDS if getattr(previous, field) != getattr(current, field)]
    if changed_fields:
        return ChangeEvent(
            product_key=current.site_product_id,
            change_type="update",
            changed_fields=changed_fields,
        )
    return ChangeEvent(product_key=current.site_product_id, change_type="noop", changed_fields=[])


def snapshot(record: ProductRecord) -> ProductSnapshot:
    return ProductSnapshot(product_key=record.site_product_id, hash_value=_hash_record(record))


def to_dict(record: ProductRecord) -> dict:
    return record.__dict__.copy()
