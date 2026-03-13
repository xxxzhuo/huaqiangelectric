from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "spm", "from"}


def normalize_url(raw_url: str) -> str:
    parsed = urlparse(raw_url.strip())
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"

    query_pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in TRACKING_PARAMS]
    query_pairs.sort(key=lambda p: p[0])

    normalized = urlunparse((scheme, netloc, path.rstrip("/") or "/", "", urlencode(query_pairs), ""))
    return normalized


def fingerprint_url(url: str) -> str:
    normalized = normalize_url(url)
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()
