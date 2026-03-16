from __future__ import annotations

import re
from urllib.parse import urlparse

from crawler.models.schemas import ProductRecord


def _extract_by_class(html: str, class_name: str) -> str | None:
    pattern = rf"<[^>]*class=['\"][^'\"]*{class_name}[^'\"]*['\"][^>]*>(.*?)</[^>]+>"
    match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return re.sub(r"<[^>]+>", "", match.group(1)).strip() or None


def _extract_tag(html: str, tag: str) -> str | None:
    match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return re.sub(r"<[^>]+>", "", match.group(1)).strip() or None


def parse_product_html(url: str, html: str) -> ProductRecord:
    title = _extract_tag(html, "h1") or _extract_by_class(html, "product-title") or "UNKNOWN"
    brand = _extract_by_class(html, "brand")
    model = _extract_by_class(html, "model")
    seller = _extract_by_class(html, "seller-name") or _extract_by_class(html, "shop-name")

    plain_text = re.sub(r"<[^>]+>", " ", html)
    price_match = re.search(r"(\d+(?:\.\d+)?)", plain_text)
    stock_match = re.search(r"库存\s*[:：]?\s*(\d+)", plain_text)

    image_urls = re.findall(r"<img[^>]+src=['\"]([^'\"]+)['\"]", html, flags=re.IGNORECASE)

    path = urlparse(url).path.strip("/")
    site_product_id = path.split("/")[-1] or path.replace("/", "_") or "unknown"

    return ProductRecord(
        site_product_id=site_product_id,
        source_url=url,
        title=title,
        brand=brand,
        model=model,
        seller_name=seller,
        price_min=float(price_match.group(1)) if price_match else None,
        price_max=float(price_match.group(1)) if price_match else None,
        stock=int(stock_match.group(1)) if stock_match else None,
        description=_extract_by_class(html, "product-desc") or _extract_by_class(html, "desc"),
        image_urls=image_urls,
    )
