from __future__ import annotations

import random
import time


class RateLimiter:
    def __init__(self, qps: float = 2.0, jitter_ms: int = 200) -> None:
        self.min_interval = 1.0 / qps
        self.jitter_ms = jitter_ms
        self._last_call = 0.0

    def wait(self) -> None:
        now = time.time()
        elapsed = now - self._last_call
        sleep_sec = max(0.0, self.min_interval - elapsed)
        sleep_sec += random.uniform(0, self.jitter_ms / 1000)
        time.sleep(sleep_sec)
        self._last_call = time.time()
