"""Configurable sequence continuity checks for StockAPI events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GapState:
    last_value: int | None = None


class GapDetector:
    def __init__(self, *, field_name: str, reset_allowed_on_date_change: bool = True) -> None:
        self.field_name = field_name
        self.reset_allowed_on_date_change = reset_allowed_on_date_change
        self._state: dict[tuple[str, str], GapState] = {}
        self._last_date: dict[tuple[str, str], str] = {}

    def observe(self, event: dict[str, Any]) -> dict[str, Any]:
        symbol = str(event.get("symbol", "") or "")
        stream_type = str(event.get("stream_type", "") or "")
        trade_date = str(event.get("trade_date", "") or "")
        fields = event.get("source_specific_fields", {}) or {}
        raw_value = fields.get(self.field_name) or event.get(self.field_name)
        key = (stream_type, symbol)
        try:
            value = int(str(raw_value))
        except (TypeError, ValueError):
            return {"status": "unknown_scope", "field_name": self.field_name, "raw_value": raw_value}
        last_date = self._last_date.get(key)
        state = self._state.setdefault(key, GapState())
        previous = state.last_value
        self._last_date[key] = trade_date
        state.last_value = value
        if previous is None:
            return {"status": "continuous", "field_name": self.field_name, "value": value, "previous": None}
        if trade_date and last_date and trade_date != last_date and self.reset_allowed_on_date_change:
            return {"status": "reset_candidate", "field_name": self.field_name, "value": value, "previous": previous}
        if value == previous:
            return {"status": "duplicate", "field_name": self.field_name, "value": value, "previous": previous}
        if value == previous + 1:
            return {"status": "continuous", "field_name": self.field_name, "value": value, "previous": previous}
        if value > previous + 1:
            return {"status": "gap", "field_name": self.field_name, "value": value, "previous": previous, "missing_count": value - previous - 1}
        return {"status": "out_of_order", "field_name": self.field_name, "value": value, "previous": previous}

