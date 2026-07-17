"""Payload parsers for StockAPI TCP V2 demo frames."""

from __future__ import annotations

import base64
import gzip
from typing import Any

from .protocol import CONTROL_MESSAGES, StreamType
from .schemas import (
    NormalizedStockApiEvent,
    default_governance,
    default_quality,
    decimal_or_none,
    parse_source_time_candidate,
)


def decompress_gzip_base64_to_text(payload: str, encoding: str = "utf-8") -> str:
    raw = gzip.decompress(base64.b64decode(payload))
    return raw.decode(encoding)


def _safe(fields: list[str], index: int) -> str:
    return fields[index] if len(fields) > index else ""


class StockApiPayloadParser:
    """Parse StockAPI payload text into normalized offline events."""

    def parse_frame(self, stream_type: StreamType | str, text: str, *, queue_version: str | None = None) -> list[dict[str, Any]]:
        stream = StreamType(stream_type)
        text = str(text or "").strip()
        if not text:
            return []
        if text in CONTROL_MESSAGES or text.startswith(("DL,", "DY2,", "CXDY2,", "QXDY2,")):
            return [
                NormalizedStockApiEvent(
                    event_type="control",
                    stream_type=stream.value,
                    source_specific_fields={"message": text},
                    quality=default_quality("control_message"),
                    governance=default_governance(stream),
                ).to_dict()
            ]
        if text.startswith("KICK,"):
            return [
                NormalizedStockApiEvent(
                    event_type="control_kick",
                    stream_type=stream.value,
                    source_specific_fields={"message": text},
                    quality=default_quality("kicked"),
                    governance=default_governance(stream),
                ).to_dict()
            ]
        if stream == StreamType.QUEUE:
            return self.parse_queue(text, version=queue_version)
        return [item.to_dict() for item in self._parse_records(stream, text)]

    def parse_queue(self, payload: str, *, version: str | None) -> list[dict[str, Any]]:
        if version == "v1":
            return [item.to_dict() for item in self._parse_records(StreamType.QUEUE, payload)]
        if version == "v2":
            fields = payload.split(",")
            event = NormalizedStockApiEvent(
                event_type="queue_v2",
                stream_type=StreamType.QUEUE.value,
                symbol=_safe(fields, 2),
                packet_no=_safe(fields, 0),
                trade_date=_safe(fields, 3),
                source_time_raw=_safe(fields, 4),
                source_time_candidate=parse_source_time_candidate(_safe(fields, 4)),
                raw_fields=fields,
                source_specific_fields={
                    "market_code": _safe(fields, 1),
                    "ask1_price_raw": _safe(fields, 5),
                    "bid1_price_raw": _safe(fields, 6),
                    "ask_queue_count_raw": _safe(fields, 7),
                    "bid_queue_count_raw": _safe(fields, 8),
                    "ask_queue_50_raw": fields[9:59],
                    "bid_queue_50_raw": fields[59:109],
                    "format_version": "v2",
                },
                quality=default_quality("queue_v2_offline_fixture"),
                governance=default_governance(StreamType.QUEUE),
            )
            return [event.to_dict()]
        return [
            NormalizedStockApiEvent(
                event_type="queue_ambiguous",
                stream_type=StreamType.QUEUE.value,
                raw_fields=payload.split(","),
                source_specific_fields={"parse_error": "AMBIGUOUS_QUEUE_FORMAT"},
                quality=default_quality("AMBIGUOUS_QUEUE_FORMAT"),
                governance=default_governance(StreamType.QUEUE),
            ).to_dict()
        ]

    def _parse_records(self, stream: StreamType, payload: str) -> list[NormalizedStockApiEvent]:
        parts = [p for p in payload.strip().split("#") if p]
        if not parts:
            return []
        records: list[NormalizedStockApiEvent] = []
        packet_no = None
        for index, part in enumerate(parts):
            fields = part.split(",")
            if index == 0 and fields:
                packet_no = fields[0]
            elif packet_no is not None and fields and fields[0] != packet_no:
                fields = [packet_no] + fields
            if stream == StreamType.MARKET:
                records.append(self._parse_market(fields))
            elif stream == StreamType.ORDER:
                records.append(self._parse_order(fields))
            elif stream == StreamType.TRAN:
                records.append(self._parse_tran(fields))
            elif stream == StreamType.QUEUE:
                records.append(self._parse_queue_v1(fields))
        return records

    def _parse_market(self, fields: list[str]) -> NormalizedStockApiEvent:
        source_time = _safe(fields, 4)
        return NormalizedStockApiEvent(
            event_type="market_snapshot_v2",
            stream_type=StreamType.MARKET.value,
            symbol=_safe(fields, 2),
            packet_no=_safe(fields, 0),
            trade_date=_safe(fields, 3),
            source_time_raw=source_time,
            source_time_candidate=parse_source_time_candidate(source_time),
            raw_fields=fields,
            source_specific_fields={
                "market_code": _safe(fields, 1),
                "status": _safe(fields, 5),
                "prev_close_raw": _safe(fields, 6),
                "open_raw": _safe(fields, 7),
                "high_raw": _safe(fields, 8),
                "low_raw": _safe(fields, 9),
                "last_raw": _safe(fields, 10),
                "last_decimal_candidate": str(decimal_or_none(_safe(fields, 10)) or ""),
                "ask_price_raw": [_safe(fields, i) for i in range(11, 21)],
                "ask_qty_raw": [_safe(fields, i) for i in range(21, 31)],
                "bid_price_raw": [_safe(fields, i) for i in range(31, 41)],
                "bid_qty_raw": [_safe(fields, i) for i in range(41, 51)],
                "trade_count_raw": _safe(fields, 51),
                "trade_volume_raw": _safe(fields, 52),
                "trade_amount_raw": _safe(fields, 53),
                "total_bid_volume_raw": _safe(fields, 54),
                "total_ask_volume_raw": _safe(fields, 55),
                "avg_bid_price_raw": _safe(fields, 56),
                "avg_ask_price_raw": _safe(fields, 57),
                "limit_up_raw": _safe(fields, 58),
                "limit_down_raw": _safe(fields, 59),
                "total_buy_orders_raw": _safe(fields, 60),
                "total_sell_orders_raw": _safe(fields, 61),
                "buy_cancel_orders_raw": _safe(fields, 62),
                "buy_cancel_volume_raw": _safe(fields, 63),
                "sell_cancel_orders_raw": _safe(fields, 64),
                "sell_cancel_volume_raw": _safe(fields, 65),
            },
            quality=default_quality("market_v2_offline_fixture"),
            governance=default_governance(StreamType.MARKET),
        )

    def _parse_order(self, fields: list[str]) -> NormalizedStockApiEvent:
        source_time = _safe(fields, 4)
        return NormalizedStockApiEvent(
            event_type="order_event_candidate_v2",
            stream_type=StreamType.ORDER.value,
            symbol=_safe(fields, 2),
            packet_no=_safe(fields, 0),
            trade_date=_safe(fields, 3),
            source_time_raw=source_time,
            source_time_candidate=parse_source_time_candidate(source_time),
            raw_fields=fields,
            source_specific_fields={
                "market_code": _safe(fields, 1),
                "order_no": _safe(fields, 5),
                "price_raw": _safe(fields, 6),
                "quantity_raw": _safe(fields, 7),
                "order_type": _safe(fields, 8),
                "side": _safe(fields, 9),
                "original_order_no": _safe(fields, 10),
                "event_sequence": _safe(fields, 11),
                "channel_no": _safe(fields, 12),
            },
            quality=default_quality("order_v2_offline_fixture"),
            governance=default_governance(StreamType.ORDER),
        )

    def _parse_tran(self, fields: list[str]) -> NormalizedStockApiEvent:
        source_time = _safe(fields, 4)
        return NormalizedStockApiEvent(
            event_type="trade_print_candidate_v2",
            stream_type=StreamType.TRAN.value,
            symbol=_safe(fields, 2),
            packet_no=_safe(fields, 0),
            trade_date=_safe(fields, 3),
            source_time_raw=source_time,
            source_time_candidate=parse_source_time_candidate(source_time),
            raw_fields=fields,
            source_specific_fields={
                "market_code": _safe(fields, 1),
                "trade_no": _safe(fields, 5),
                "price_raw": _safe(fields, 6),
                "quantity_raw": _safe(fields, 7),
                "amount_raw": _safe(fields, 8),
                "side": _safe(fields, 9),
                "trade_type": _safe(fields, 10),
                "original_no": _safe(fields, 11),
                "sell_order_no": _safe(fields, 12),
                "buy_order_no": _safe(fields, 13),
            },
            quality=default_quality("tran_v2_offline_fixture"),
            governance=default_governance(StreamType.TRAN),
        )

    def _parse_queue_v1(self, fields: list[str]) -> NormalizedStockApiEvent:
        source_time = _safe(fields, 4)
        return NormalizedStockApiEvent(
            event_type="queue_v1",
            stream_type=StreamType.QUEUE.value,
            symbol=_safe(fields, 2),
            packet_no=_safe(fields, 0),
            trade_date=_safe(fields, 3),
            source_time_raw=source_time,
            source_time_candidate=parse_source_time_candidate(source_time),
            raw_fields=fields,
            source_specific_fields={
                "market_code": _safe(fields, 1),
                "queue_fields_raw": fields[5:],
                "format_version": "v1",
            },
            quality=default_quality("queue_v1_offline_fixture"),
            governance=default_governance(StreamType.QUEUE),
        )

