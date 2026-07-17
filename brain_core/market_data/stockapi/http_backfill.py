"""Offline HTTP backfill interface and mock implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BackfillRequest:
    stream_type: str
    symbol: str
    trade_date: str
    offset: int = 0
    reason: str = "gap_detected"
    metadata: dict[str, Any] = field(default_factory=dict)


class MockHttpBackfillClient:
    """No-network backfill mock used for tests and planning."""

    def __init__(self) -> None:
        self.requests: list[BackfillRequest] = []

    def request_backfill(self, request: BackfillRequest) -> dict[str, Any]:
        self.requests.append(request)
        return {
            "status": "mocked",
            "request": {
                "stream_type": request.stream_type,
                "symbol": request.symbol,
                "trade_date": request.trade_date,
                "offset": request.offset,
                "reason": request.reason,
                "metadata": dict(request.metadata),
            },
            "raw_saved": False,
            "events": [],
            "network_used": False,
        }

