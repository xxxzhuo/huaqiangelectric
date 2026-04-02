from __future__ import annotations

from dataclasses import dataclass, field

from crawler.models.schemas import ChangeEvent


@dataclass
class CrawlMetrics:
    discovered_urls: int = 0
    crawled_pages: int = 0
    parsed_products: int = 0
    upserted_products: int = 0
    failed_pages: int = 0
    change_counts: dict[str, int] = field(
        default_factory=lambda: {"new": 0, "update": 0, "delist": 0, "relist": 0, "noop": 0}
    )

    def record_change(self, event: ChangeEvent) -> None:
        self.change_counts[event.change_type] = self.change_counts.get(event.change_type, 0) + 1

    def as_dict(self) -> dict:
        return {
            "discovered_urls": self.discovered_urls,
            "crawled_pages": self.crawled_pages,
            "parsed_products": self.parsed_products,
            "upserted_products": self.upserted_products,
            "failed_pages": self.failed_pages,
            "change_counts": self.change_counts,
        }
