"""Strict source-byte indexing.  All offsets are byte offsets, never characters."""

from __future__ import annotations

from dataclasses import dataclass


class Utf8IndexError(ValueError):
    """Raised when a source cannot safely be represented as strict UTF-8."""


@dataclass(frozen=True, slots=True)
class LineRecord:
    number: int
    start: int
    end: int
    content_end: int


class ByteTruthIndex:
    """A minimal deterministic index over copied, immutable source bytes."""

    __slots__ = ("_data", "_text", "_lines")

    def __init__(self, data: bytes) -> None:
        if not isinstance(data, bytes):
            raise TypeError("source data must be bytes")
        try:
            text = data.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise Utf8IndexError("source is not strict UTF-8") from exc
        # E53_0XED_MUTATION_ANCHOR: strict decoding must not be weakened.
        self._data = bytes(data)
        self._text = text
        self._lines = self._scan_lines(data)

    @staticmethod
    def _scan_lines(data: bytes) -> tuple[LineRecord, ...]:
        records: list[LineRecord] = []
        start = 0
        number = 1
        for index, value in enumerate(data):
            if value == 0x0A:
                content_end = index - 1 if index > start and data[index - 1] == 0x0D else index
                records.append(LineRecord(number, start, index + 1, content_end))
                start = index + 1
                number += 1
        if start < len(data) or not records:
            records.append(LineRecord(number, start, len(data), len(data)))
        return tuple(records)

    @property
    def byte_length(self) -> int:
        return len(self._data)

    @property
    def line_records(self) -> tuple[LineRecord, ...]:
        return self._lines

    def slice(self, start: int, end: int) -> bytes:
        if not (isinstance(start, int) and isinstance(end, int) and 0 <= start <= end <= len(self._data)):
            raise Utf8IndexError("byte slice is outside the exact source")
        return self._data[start:end]

    def text_slice(self, start: int, end: int) -> str:
        try:
            return self.slice(start, end).decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise Utf8IndexError("slice cuts a UTF-8 code point") from exc

    def boundaries_are_utf8(self, start: int, end: int) -> bool:
        try:
            self.text_slice(start, end)
        except Utf8IndexError:
            return False
        return True
