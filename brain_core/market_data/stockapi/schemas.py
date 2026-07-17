"""Schema helpers for StockAPI V2 normalized events."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from .protocol import StreamType


FIELD_SEMANTICS_VERSION = "stockapi-tcp-v2-demo-0015"
SCHEMA_VERSION = "stockapi-l2-demo-adapter-v0.1"


@dataclass
class NormalizedStockApiEvent:
    event_type: str
    stream_type: str
    symbol: str = ""
    packet_no: str = ""
    trade_date: str = ""
    source_time_raw: str = ""
    source_time_candidate: str = ""
    raw_fields: list[str] = field(default_factory=list)
    source_specific_fields: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    governance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "field_semantics_version": FIELD_SEMANTICS_VERSION,
            "event_type": self.event_type,
            "stream_type": self.stream_type,
            "symbol": self.symbol,
            "packet_no": self.packet_no,
            "trade_date": self.trade_date,
            "source_time_raw": self.source_time_raw,
            "source_time_candidate": self.source_time_candidate,
            "raw_fields": list(self.raw_fields),
            "source_specific_fields": dict(self.source_specific_fields),
            "quality": dict(self.quality),
            "governance": dict(self.governance),
        }


def decimal_or_none(value: str) -> Decimal | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def parse_source_time_candidate(raw: str) -> str:
    """Parse `135306980` as candidate `13:53:06.980`, preserving raw elsewhere."""

    text = str(raw or "").strip()
    if len(text) == 9 and text.isdigit():
        return f"{text[0:2]}:{text[2:4]}:{text[4:6]}.{text[6:9]}"
    if len(text) == 6 and text.isdigit():
        return f"{text[0:2]}:{text[2:4]}:{text[4:6]}"
    return ""


def default_governance(stream_type: StreamType | str) -> dict[str, Any]:
    return {
        "research_only": True,
        "live_trading_enabled": False,
        "source": "stockapi_tcp_v2_demo",
        "capability_claim": str(stream_type.value if isinstance(stream_type, StreamType) else stream_type),
        "raw_l2_gate_cleared": False,
        "ten_level_verified": False,
        "raw_trade_tick_verified": False,
        "raw_order_event_verified": False,
        "queue_50_verified": False,
        "auction_trajectory_verified": False,
    }


def default_quality(status: str = "parsed_from_offline_fixture") -> dict[str, Any]:
    return {
        "quality_score": 0.62,
        "evidence_level": "offline_fixture",
        "source_reliability": 0.58,
        "freshness": 1.0,
        "validation_status": status,
        "out_of_sample_result": "not_applicable",
        "failure_count": 0,
        "conflict_count": 0,
        "human_reviewed": False,
        "status": "Experimental",
    }

