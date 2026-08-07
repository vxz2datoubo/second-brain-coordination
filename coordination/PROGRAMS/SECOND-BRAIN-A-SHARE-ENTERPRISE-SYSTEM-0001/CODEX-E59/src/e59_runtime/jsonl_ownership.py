"""Whole-source JSONL ownership retained from the selected E58 regression area."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterator


class JsonlOwnershipError(ValueError):
    def __init__(self, code: str, offset: int) -> None:
        self.code = code
        self.offset = offset
        super().__init__(f"{code} at byte offset {offset}")


@dataclass(frozen=True, slots=True)
class ByteRange:
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class OwnedSegment:
    kind: str
    raw: ByteRange
    line_index: int


@dataclass(frozen=True, slots=True)
class JsonlOwnership:
    source_sha256: str
    byte_length: int
    segments: tuple[OwnedSegment, ...]
    record_count: int
    status: str

    def assert_complete_partition(self) -> None:
        cursor = 0
        for segment in self.segments:
            if segment.raw.start != cursor or segment.raw.end < segment.raw.start:
                raise JsonlOwnershipError("JSONL_PARTITION_GAP_OR_OVERLAP", cursor)
            cursor = segment.raw.end
        if cursor != self.byte_length:
            raise JsonlOwnershipError("JSONL_PARTITION_INCOMPLETE", cursor)


def _lines(source: bytes) -> Iterator[tuple[int, int, int, int]]:
    """Yield content and terminator offsets without dropping CRLF or blanks."""

    start = 0
    index = 0
    while index < len(source):
        if source[index] not in (10, 13):
            index += 1
            continue
        content_end = index
        terminator_end = index + 1
        if source[index] == 13 and terminator_end < len(source) and source[terminator_end] == 10:
            terminator_end += 1
        yield start, content_end, content_end, terminator_end
        start = terminator_end
        index = terminator_end
    if start < len(source):
        yield start, len(source), len(source), len(source)


def _surrogate_offset(value: object) -> int | None:
    if isinstance(value, str):
        for index, character in enumerate(value):
            if 0xD800 <= ord(character) <= 0xDFFF:
                return index
    if isinstance(value, list):
        for item in value:
            found = _surrogate_offset(item)
            if found is not None:
                return found
    if isinstance(value, dict):
        for key, item in value.items():
            found = _surrogate_offset(key)
            if found is not None:
                return found
            found = _surrogate_offset(item)
            if found is not None:
                return found
    return None


def parse_jsonl_whole_source(source: bytes) -> JsonlOwnership:
    segments: list[OwnedSegment] = []
    records = 0
    line_index = 0
    for content_start, content_end, terminator_start, terminator_end in _lines(source):
        content = source[content_start:content_end]
        if content:
            if content.strip():
                try:
                    decoded = content.decode("utf-8", "strict")
                except UnicodeDecodeError as exc:
                    raise JsonlOwnershipError("NON_UTF8_JSONL_RECORD", content_start + exc.start) from exc
                try:
                    loaded = json.loads(decoded)
                except json.JSONDecodeError as exc:
                    raise JsonlOwnershipError("INVALID_JSONL_RECORD", content_start + len(decoded[: exc.pos].encode("utf-8"))) from exc
                if _surrogate_offset(loaded) is not None:
                    raw_offset = content.find(b"\\uD")
                    if raw_offset < 0:
                        raw_offset = content.find(b"\\ud")
                    raise JsonlOwnershipError("ISOLATED_SURROGATE", content_start + max(raw_offset, 0))
                segments.append(OwnedSegment("JSON_RECORD", ByteRange(content_start, content_end), line_index))
                records += 1
            else:
                segments.append(OwnedSegment("BLANK_LINE", ByteRange(content_start, content_end), line_index))
        if terminator_end > terminator_start:
            segments.append(OwnedSegment("LINE_TERMINATOR", ByteRange(terminator_start, terminator_end), line_index))
        line_index += 1
    status = "EMPTY_SOURCE" if not source else ("NO_JSON_RECORDS" if records == 0 else "COMPLETE")
    ownership = JsonlOwnership(sha256(source).hexdigest(), len(source), tuple(segments), records, status)
    ownership.assert_complete_partition()
    return ownership
