"""Regenerable synthetic TDX .day records for tests and offline CI."""

from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class SyntheticDayRecord:
    date_raw: int = 20260105
    open_raw: int = 1000
    high_raw: int = 1100
    low_raw: int = 900
    close_raw: int = 1050
    amount_float: float = 123456.0
    volume_raw: int = 10000
    reserved_raw: int = 0

    def encode(self) -> bytes:
        return struct.pack(
            "<IIIIIfII",
            self.date_raw,
            self.open_raw,
            self.high_raw,
            self.low_raw,
            self.close_raw,
            self.amount_float,
            self.volume_raw,
            self.reserved_raw,
        )


def encode_records(*records: SyntheticDayRecord) -> bytes:
    return b"".join(record.encode() for record in records)
