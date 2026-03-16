from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from crawler.anti_bot.limiter import RateLimiter


@dataclass
class FetchResult:
    url: str
    status_code: int
    body: str
    elapsed_ms: int


class HttpFetcher:
    def __init__(
        self,
        timeout: int = 15,
        retries: int = 3,
        backoff_seconds: float = 1.0,
        user_agent: str = "Mozilla/5.0 (compatible; HQEWBot/0.1)",
        limiter: RateLimiter | None = None,
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.user_agent = user_agent
        self.limiter = limiter or RateLimiter(qps=1.0)

    def fetch(self, url: str) -> FetchResult:
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                self.limiter.wait()
                start = time.perf_counter()
                req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8", errors="ignore")
                    elapsed_ms = int((time.perf_counter() - start) * 1000)
                    return FetchResult(url=url, status_code=resp.getcode(), body=body, elapsed_ms=elapsed_ms)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt == self.retries:
                    break
                time.sleep(self.backoff_seconds * attempt)
        raise RuntimeError(f"Failed to fetch {url} after {self.retries} attempts: {last_error}")
