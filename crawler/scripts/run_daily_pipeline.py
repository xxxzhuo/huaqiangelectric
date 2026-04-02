from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from crawler.models.schemas import ChangeEvent, UrlTask
from crawler.monitor.metrics import CrawlMetrics
from crawler.parsers.product_parser import parse_product_html
from crawler.pipelines.diff import detect_change
from crawler.queue.task_queue import InMemoryTaskQueue
from crawler.spiders.discover import DiscoverSpider
from crawler.spiders.fetcher import HttpFetcher
from crawler.spiders.url_utils import fingerprint_url
from crawler.storage.raw_store import save_raw_page
from crawler.storage.sqlite_repository import SQLiteProductRepository


def run_pipeline(
    html_pages: list[tuple[str, str]],
    db_path: str = "data/crawler.db",
    reconcile_delist: bool = True,
) -> tuple[list[ChangeEvent], CrawlMetrics]:
    repo = SQLiteProductRepository(db_path=db_path)
    metrics = CrawlMetrics(crawled_pages=len(html_pages))
    events: list[ChangeEvent] = []

    existing_ids = set(repo.list_current_product_ids()) if reconcile_delist else set()
    seen_ids: set[str] = set()

    for url, html in html_pages:
        try:
            record = parse_product_html(url, html)
            metrics.parsed_products += 1
            seen_ids.add(record.site_product_id)

            previous = repo.get(record.site_product_id)
            change = detect_change(previous=previous, current=record)
            events.append(change)
            metrics.record_change(change)

            repo.upsert(record)
            if change.change_type != "noop":
                repo.save_change(record, change)
            metrics.upserted_products += 1
        except Exception:
            metrics.failed_pages += 1

    if reconcile_delist:
        stale_ids = sorted(existing_ids - seen_ids)
        for stale_id in stale_ids:
            event = repo.mark_delisted(stale_id)
            if event is not None:
                events.append(event)
                metrics.record_change(event)

    return events, metrics


def run_from_urls(
    urls: list[str],
    db_path: str = "data/crawler.db",
    raw_dir: str = "data/raw",
    reconcile_delist: bool = True,
) -> tuple[list[ChangeEvent], CrawlMetrics]:
    fetcher = HttpFetcher()
    html_pages: list[tuple[str, str]] = []
    failed = 0

    for url in urls:
        try:
            result = fetcher.fetch(url)
            save_raw_page(base_dir=raw_dir, site="s.hqew.com", url_fingerprint=fingerprint_url(url), body=result.body)
            html_pages.append((result.url, result.body))
        except Exception:
            failed += 1

    events, metrics = run_pipeline(html_pages, db_path=db_path, reconcile_delist=reconcile_delist)
    metrics.crawled_pages = len(html_pages)
    metrics.failed_pages += failed
    return events, metrics


def discover_tasks(seed_url: str, max_urls: int = 200) -> list[UrlTask]:
    fetcher = HttpFetcher()
    spider = DiscoverSpider()
    queue = InMemoryTaskQueue()

    seed_html = fetcher.fetch(seed_url).body
    links = spider.extract_links(seed_url, seed_html)

    for link in links[:max_urls]:
        queue.push(
            UrlTask(
                url=link,
                url_type="detail",
                depth=1,
                priority=50,
                fingerprint=fingerprint_url(link),
            )
        )

    tasks: list[UrlTask] = []
    while len(queue) > 0:
        item = queue.pop()
        if item:
            tasks.append(item)
    return tasks


def run_end_to_end(seed_url: str, db_path: str = "data/crawler.db", raw_dir: str = "data/raw", max_urls: int = 50) -> dict:
    tasks = discover_tasks(seed_url=seed_url, max_urls=max_urls)
    urls = [task.url for task in tasks]
    events, metrics = run_from_urls(urls=urls, db_path=db_path, raw_dir=raw_dir, reconcile_delist=True)
    metrics.discovered_urls = len(tasks)
    return {
        "seed_url": seed_url,
        "discovered": len(tasks),
        "events": [asdict(e) for e in events],
        "metrics": metrics.as_dict(),
        "db_path": db_path,
        "raw_dir": raw_dir,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HQEW daily crawler pipeline runner")
    parser.add_argument("--seed-url", default="https://s.hqew.com/", help="Seed URL used for discover stage")
    parser.add_argument("--db-path", default="data/crawler.db", help="SQLite database path")
    parser.add_argument("--raw-dir", default="data/raw", help="Raw HTML output directory")
    parser.add_argument("--max-urls", type=int, default=50, help="Maximum discovered URLs to crawl")
    parser.add_argument("--offline", action="store_true", help="Run a built-in offline sample without network")
    parser.add_argument("--reset-db", action="store_true", help="Delete existing SQLite DB before run")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.reset_db and Path(args.db_path).exists():
        Path(args.db_path).unlink()

    if args.offline:
        sample = [
            (
                "https://s.hqew.com/product/ABC123",
                "<html><h1>STM32F103</h1><div class='brand'>ST</div><div>库存: 100</div></html>",
            )
        ]
        events, metrics = run_pipeline(sample, db_path=args.db_path, reconcile_delist=False)
        print(json.dumps({"events": [asdict(e) for e in events], "metrics": metrics.as_dict()}, ensure_ascii=False, default=str))
        return

    result = run_end_to_end(seed_url=args.seed_url, db_path=args.db_path, raw_dir=args.raw_dir, max_urls=args.max_urls)
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
