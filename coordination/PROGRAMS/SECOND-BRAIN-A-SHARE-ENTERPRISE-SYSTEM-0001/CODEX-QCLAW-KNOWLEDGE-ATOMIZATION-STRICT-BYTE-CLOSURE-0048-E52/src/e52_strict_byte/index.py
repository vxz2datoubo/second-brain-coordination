"""Immutable byte truth index and canonical line model for E52 S0."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence


class ScannerProgressError(ValueError):
    """Raised when a scanner branch fails to advance the byte cursor."""


@dataclass(frozen=True, slots=True)
class Chunk:
    byte_start: int
    byte_end: int
    codepoint_index: int
    codepoint: str


@dataclass(frozen=True, slots=True)
class LineRecord:
    """One line plus its original terminator, never an ownership span itself."""

    line_index: int
    content_start: int
    content_end: int
    terminator_start: int | None
    terminator_end: int | None
    is_blank: bool
    has_trailing_empty_line: bool


def _scan_utf8_strict(source: bytes) -> None:
    """Validate UTF-8 while retaining an explicit, mutation-testable 0xED path."""
    total = len(source)
    i = 0
    while i < total:
        before = i
        first = source[i]
        if first < 0x80:
            next_index = i + 1
        elif 0xC2 <= first <= 0xDF:
            if i + 1 >= total or source[i + 1] & 0xC0 != 0x80:
                raise ValueError("invalid two-byte UTF-8 sequence")
            next_index = i + 2
        elif 0xE0 <= first <= 0xEF:
            if i + 2 >= total:
                raise ValueError("truncated three-byte UTF-8 sequence")
            second, third = source[i + 1], source[i + 2]
            if second & 0xC0 != 0x80 or third & 0xC0 != 0x80:
                raise ValueError("invalid three-byte UTF-8 continuation")
            if first == 0xE0 and second < 0xA0:
                raise ValueError("overlong three-byte UTF-8 sequence")
            if first == 0xED and second >= 0xA0:
                raise ValueError("UTF-8 surrogate sequence is forbidden")
            next_index = i + 3  # E52_0XED_PROGRESS_ANCHOR
        elif 0xF0 <= first <= 0xF4:
            if i + 3 >= total:
                raise ValueError("truncated four-byte UTF-8 sequence")
            second, third, fourth = source[i + 1], source[i + 2], source[i + 3]
            if any(byte & 0xC0 != 0x80 for byte in (second, third, fourth)):
                raise ValueError("invalid four-byte UTF-8 continuation")
            if first == 0xF0 and second < 0x90:
                raise ValueError("overlong four-byte UTF-8 sequence")
            if first == 0xF4 and second > 0x8F:
                raise ValueError("UTF-8 codepoint exceeds U+10FFFF")
            next_index = i + 4
        else:
            raise ValueError("invalid UTF-8 leading byte")
        i = next_index
        if i <= before:  # E52_PROGRESS_GUARD_ANCHOR
            raise ScannerProgressError("UTF-8 scanner made no progress")


class ByteTruthIndex:
    """Finalized immutable UTF-8 byte index with explicit offset semantics."""

    __slots__ = (
        "_source_bytes",
        "_chunks",
        "_byte_to_chunk_index",
        "_boundary_to_codepoint",
        "_line_records",
        "_total_bytes",
        "_codepoint_count",
        "_frozen",
    )

    def __init__(self, source: bytes):
        object.__setattr__(self, "_frozen", False)
        immutable_source = bytes(source)
        _scan_utf8_strict(immutable_source)
        try:
            text = immutable_source.decode("utf-8", "strict")
        except UnicodeDecodeError as error:
            raise ValueError("invalid UTF-8") from error

        chunks: list[Chunk] = []
        byte_to_chunk: list[int] = []
        boundary_to_codepoint: dict[int, int] = {0: 0}
        byte_offset = 0
        for codepoint_index, character in enumerate(text):
            encoded = character.encode("utf-8")
            next_offset = byte_offset + len(encoded)
            chunks.append(Chunk(byte_offset, next_offset, codepoint_index, character))
            byte_to_chunk.extend([codepoint_index] * len(encoded))
            boundary_to_codepoint[next_offset] = codepoint_index + 1
            byte_offset = next_offset

        object.__setattr__(self, "_source_bytes", immutable_source)
        object.__setattr__(self, "_chunks", tuple(chunks))
        object.__setattr__(self, "_byte_to_chunk_index", tuple(byte_to_chunk))
        object.__setattr__(self, "_boundary_to_codepoint", MappingProxyType(dict(boundary_to_codepoint)))
        object.__setattr__(self, "_line_records", self._build_line_records(immutable_source))
        object.__setattr__(self, "_total_bytes", len(immutable_source))
        object.__setattr__(self, "_codepoint_count", len(text))
        object.__setattr__(self, "_frozen", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError(f"ByteTruthIndex is finalized and immutable: {name}")
        object.__setattr__(self, name, value)

    @staticmethod
    def _build_line_records(source: bytes) -> tuple[LineRecord, ...]:
        if not source:
            return ()
        records: list[LineRecord] = []
        cursor = 0
        line_index = 0
        total = len(source)
        while cursor < total:
            content_start = cursor
            while cursor < total and source[cursor] not in (0x0A, 0x0D):
                cursor += 1
            content_end = cursor
            terminator_start: int | None = None
            terminator_end: int | None = None
            if cursor < total:
                terminator_start = cursor
                if source[cursor] == 0x0D and cursor + 1 < total and source[cursor + 1] == 0x0A:
                    cursor += 2
                else:
                    cursor += 1
                terminator_end = cursor
            records.append(
                LineRecord(
                    line_index=line_index,
                    content_start=content_start,
                    content_end=content_end,
                    terminator_start=terminator_start,
                    terminator_end=terminator_end,
                    is_blank=content_start == content_end,
                    has_trailing_empty_line=False,
                )
            )
            line_index += 1
        if records[-1].terminator_end is not None:
            records.append(
                LineRecord(
                    line_index=line_index,
                    content_start=total,
                    content_end=total,
                    terminator_start=None,
                    terminator_end=None,
                    is_blank=True,
                    has_trailing_empty_line=True,
                )
            )
        return tuple(records)

    @property
    def total_bytes(self) -> int:
        return self._total_bytes

    @property
    def codepoint_count(self) -> int:
        return self._codepoint_count

    @property
    def source_bytes(self) -> bytes:
        return self._source_bytes

    def chunks(self) -> tuple[Chunk, ...]:
        return self._chunks

    def line_records(self) -> tuple[LineRecord, ...]:
        return self._line_records

    def boundary_to_codepoint(self) -> Mapping[int, int]:
        return self._boundary_to_codepoint

    def codepoint_index_at_boundary(self, offset: int) -> int:
        try:
            return self._boundary_to_codepoint[offset]
        except KeyError as error:
            raise ValueError(f"offset is not a UTF-8 codepoint boundary: {offset}") from error

    def chunk_containing_byte(self, offset: int) -> Chunk:
        if offset < 0 or offset >= self._total_bytes:
            raise IndexError(f"byte offset outside [0, {self._total_bytes}): {offset}")
        return self._chunks[self._byte_to_chunk_index[offset]]
