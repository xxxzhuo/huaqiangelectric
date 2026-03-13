from pathlib import Path

from crawler.models.schemas import ProductRecord
from crawler.storage.sqlite_repository import SQLiteProductRepository


def test_sqlite_repository_upsert_and_get(tmp_path: Path) -> None:
    db = tmp_path / "products.db"
    repo = SQLiteProductRepository(str(db))

    record = ProductRecord(
        site_product_id="ABC123",
        source_url="https://s.hqew.com/product/ABC123",
        title="STM32F103",
        brand="ST",
        stock=100,
    )
    repo.upsert(record)

    loaded = repo.get("ABC123")
    assert loaded is not None
    assert loaded.title == "STM32F103"
    assert loaded.brand == "ST"
