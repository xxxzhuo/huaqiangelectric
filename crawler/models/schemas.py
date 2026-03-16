from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from urllib.parse import urlparse


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")


@dataclass
class UrlTask:
    url: str
    url_type: Literal["category", "search", "shop", "detail"]
    depth: int = 0
    priority: int = 50
    retry_count: int = 0
    discover_date: datetime = field(default_factory=datetime.utcnow)
    fingerprint: str = ""

    def __post_init__(self) -> None:
        _validate_url(self.url)


@dataclass
class ProductRecord:
    site_product_id: str
    source_url: str
    title: str
    site: str = "s.hqew.com"
    brand: str | None = None
    model: str | None = None
    package: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    currency: str = "CNY"
    stock: int | None = None
    moq: int | None = None
    seller_name: str | None = None
    seller_id: str | None = None
    seller_region: str | None = None
    category_path: str | None = None
    description: str | None = None
    image_urls: list[str] = field(default_factory=list)
    param_json: dict[str, str] = field(default_factory=dict)
    first_seen_at: datetime = field(default_factory=datetime.utcnow)
    last_seen_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        _validate_url(self.source_url)


@dataclass
class ChangeEvent:
    product_key: str
    change_type: Literal["new", "update", "delist", "relist"]
    changed_fields: list[str] = field(default_factory=list)
    at: datetime = field(default_factory=datetime.utcnow)
