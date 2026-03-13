from __future__ import annotations

from collections.abc import Iterable

from crawler.models.schemas import ProductRecord


class InMemoryProductRepository:
    """MVP repository, can be replaced by MySQL implementation."""

    def __init__(self) -> None:
        self._records: dict[str, ProductRecord] = {}

    def get(self, product_id: str) -> ProductRecord | None:
        return self._records.get(product_id)

    def upsert(self, record: ProductRecord) -> None:
        self._records[record.site_product_id] = record

    def list_all(self) -> Iterable[ProductRecord]:
        return self._records.values()
