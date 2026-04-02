from datetime import datetime, timezone
from pathlib import Path

from crawler.models.schemas import UrlTask
from crawler.queue.task_queue import InMemoryTaskQueue
from crawler.spiders.url_utils import fingerprint_url
from crawler.storage.raw_store import save_raw_page


def test_task_queue_priority_and_dedup() -> None:
    q = InMemoryTaskQueue()
    t1 = UrlTask(url="https://s.hqew.com/product/B", url_type="detail", priority=20, fingerprint=fingerprint_url("https://s.hqew.com/product/B"))
    t2 = UrlTask(url="https://s.hqew.com/product/A", url_type="detail", priority=10, fingerprint=fingerprint_url("https://s.hqew.com/product/A"))
    t3 = UrlTask(url="https://s.hqew.com/product/A", url_type="detail", priority=1, fingerprint=fingerprint_url("https://s.hqew.com/product/A"))

    assert q.push(t1) is True
    assert q.push(t2) is True
    assert q.push(t3) is False

    first = q.pop()
    second = q.pop()
    assert first is not None and first.url.endswith("/A")
    assert second is not None and second.url.endswith("/B")


def test_save_raw_page(tmp_path: Path) -> None:
    output = save_raw_page(
        base_dir=str(tmp_path),
        site="s.hqew.com",
        url_fingerprint="abc123",
        body="<html>ok</html>",
        when=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    assert output.exists()
    assert "dt=2026-01-02" in str(output)
    assert output.read_text(encoding="utf-8") == "<html>ok</html>"
