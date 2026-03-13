from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CrawlMetrics:
    discovered_urls: int = 0
    crawled_pages: int = 0
    parsed_products: int = 0
    upserted_products: int = 0
    failed_pages: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "discovered_urls": self.discovered_urls,
            "crawled_pages": self.crawled_pages,
            "parsed_products": self.parsed_products,
            "upserted_products": self.upserted_products,
            "failed_pages": self.failed_pages,
        }
