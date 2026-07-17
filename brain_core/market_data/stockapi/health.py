"""Backpressure and health helpers for StockAPI runtime skeletons."""

from __future__ import annotations

from dataclasses import dataclass
import queue
from typing import Any


@dataclass
class QueueMetrics:
    queue_high_watermark: int = 0
    dropped_count: int = 0
    parse_error_count: int = 0


class BoundedEventQueue:
    def __init__(self, maxsize: int = 10_000, *, drop_policy: str = "drop_newest") -> None:
        self.queue: queue.Queue[Any] = queue.Queue(maxsize=max(1, int(maxsize)))
        self.drop_policy = drop_policy
        self.metrics = QueueMetrics()

    def put(self, item: Any) -> bool:
        try:
            self.queue.put_nowait(item)
            self.metrics.queue_high_watermark = max(self.metrics.queue_high_watermark, self.queue.qsize())
            return True
        except queue.Full:
            self.metrics.dropped_count += 1
            if self.drop_policy == "raise":
                raise
            return False

    def get(self, timeout: float | None = None) -> Any:
        return self.queue.get(timeout=timeout)

