"""Append-only raw and normalized event writer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .framing import FrameRecord


class AppendOnlyRawWriter:
    def __init__(self, root: Path, *, batch_size: int = 100) -> None:
        self.root = Path(root)
        self.batch_size = max(1, int(batch_size))
        self.raw_count = 0
        self.normalized_count = 0
        self.root.mkdir(parents=True, exist_ok=True)

    def write_raw_frame(self, frame: FrameRecord, *, trade_date: str = "unknown", stream_type: str = "unknown", symbol: str = "unknown") -> Path:
        path = self.root / "raw" / trade_date / stream_type / f"{symbol}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(frame.to_jsonable(), ensure_ascii=False, sort_keys=True) + "\n")
        self.raw_count += 1
        return path

    def write_normalized_event(self, event: dict[str, Any]) -> Path:
        trade_date = str(event.get("trade_date") or "unknown")
        stream_type = str(event.get("stream_type") or "unknown")
        symbol = str(event.get("symbol") or "unknown")
        path = self.root / "normalized" / trade_date / stream_type / f"{symbol}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        self.normalized_count += 1
        return path

    def close(self) -> dict[str, int]:
        return {"raw_count": self.raw_count, "normalized_count": self.normalized_count}

