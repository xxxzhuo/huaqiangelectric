from pathlib import Path

from crawler.scripts.run_daily_pipeline import run_pipeline
from crawler.storage.sqlite_repository import SQLiteProductRepository


def test_run_pipeline_persists_changes_and_noop(tmp_path: Path) -> None:
    db_path = tmp_path / "crawler.db"
    html_pages = [
        ("https://s.hqew.com/product/ABC123", "<html><h1>STM32F103</h1><div class='brand'>ST</div><div>库存: 100</div></html>"),
        ("https://s.hqew.com/product/ABC123", "<html><h1>STM32F103</h1><div class='brand'>ST</div><div>库存: 120</div></html>"),
        ("https://s.hqew.com/product/ABC123", "<html><h1>STM32F103</h1><div class='brand'>ST</div><div>库存: 120</div></html>"),
    ]

    events, metrics = run_pipeline(html_pages=html_pages, db_path=str(db_path), reconcile_delist=False)

    assert len(events) == 3
    assert events[0].change_type == "new"
    assert events[1].change_type == "update"
    assert events[2].change_type == "noop"
    assert metrics.upserted_products == 3
    assert metrics.change_counts["new"] == 1
    assert metrics.change_counts["update"] == 1
    assert metrics.change_counts["noop"] == 1

    repo = SQLiteProductRepository(str(db_path))
    changes = repo.list_changes(limit=10)
    # noop 不落地到 change_events
    assert len(changes) == 2


def test_run_pipeline_reconcile_delist(tmp_path: Path) -> None:
    db_path = tmp_path / "crawler.db"

    # 第一次抓到 ABC123
    run_pipeline(
        html_pages=[("https://s.hqew.com/product/ABC123", "<html><h1>STM32F103</h1><div>库存: 100</div></html>")],
        db_path=str(db_path),
        reconcile_delist=True,
    )

    # 第二次为空，触发 delist
    events, metrics = run_pipeline(html_pages=[], db_path=str(db_path), reconcile_delist=True)
    assert any(e.change_type == "delist" and e.product_key == "ABC123" for e in events)
    assert metrics.change_counts["delist"] == 1

    repo = SQLiteProductRepository(str(db_path))
    record = repo.get("ABC123")
    assert record is not None
    assert record.status == "delist"
