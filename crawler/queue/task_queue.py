from __future__ import annotations

import heapq
from dataclasses import dataclass, field

from crawler.models.schemas import UrlTask


@dataclass(order=True)
class _QueueItem:
    priority: int
    seq: int
    task: UrlTask = field(compare=False)


class InMemoryTaskQueue:
    """Priority queue with fingerprint dedupe for crawl tasks."""

    def __init__(self) -> None:
        self._heap: list[_QueueItem] = []
        self._seen: set[str] = set()
        self._seq = 0

    def push(self, task: UrlTask) -> bool:
        if task.fingerprint in self._seen:
            return False
        self._seen.add(task.fingerprint)
        self._seq += 1
        heapq.heappush(self._heap, _QueueItem(priority=task.priority, seq=self._seq, task=task))
        return True

    def pop(self) -> UrlTask | None:
        if not self._heap:
            return None
        return heapq.heappop(self._heap).task

    def __len__(self) -> int:
        return len(self._heap)
