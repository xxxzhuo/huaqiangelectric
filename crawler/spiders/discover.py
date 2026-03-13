from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import urljoin

from crawler.models.schemas import UrlTask
from crawler.spiders.url_utils import fingerprint_url, normalize_url


class DiscoverSpider:
    """Simplified discover spider for category/search/shop pages."""

    def __init__(self, allowed_host: str = "s.hqew.com") -> None:
        self.allowed_host = allowed_host

    def extract_links(self, base_url: str, html: str) -> list[str]:
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
        links: list[str] = []
        for href in hrefs:
            absolute = urljoin(base_url, href)
            if self.allowed_host in absolute:
                links.append(normalize_url(absolute))
        return sorted(set(links))

    def build_tasks(self, urls: Iterable[str], url_type: str = "detail", depth: int = 1) -> list[UrlTask]:
        tasks: list[UrlTask] = []
        for url in urls:
            tasks.append(
                UrlTask(
                    url=url,
                    url_type=url_type,
                    depth=depth,
                    fingerprint=fingerprint_url(url),
                )
            )
        return tasks
