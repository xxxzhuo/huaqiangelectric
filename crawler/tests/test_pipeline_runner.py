from pathlib import Path

from crawler.scripts.run_daily_pipeline import run_pipeline
from crawler.storage.sqlite_repository import SQLiteProductRepository


def test_run_pipeline_persists_changes(tmp_path: Path) -> None:
    db_path = tmp_path / "crawler.db"
    html_pages = [
        ("https://s.hqew.com/product/ABC123", "<html><h1>STM32F103</h1><div class='brand'>ST</div><div>库存: 100</div></html>"),
        ("https://s.hqew.com/product/ABC123", "<html><h1>STM32F103</h1><div class='brand'>ST</div><div>库存: 120</div></html>"),
    ]

    events, metrics = run_pipeline(html_pages=html_pages, db_path=str(db_path))

    assert len(events) == 2
    assert events[0].change_type == "new"
    assert events[1].change_type == "update"
    assert metrics.upserted_products == 2

    repo = SQLiteProductRepository(str(db_path))
    changes = repo.list_changes(limit=10)
    assert len(changes) >= 2
