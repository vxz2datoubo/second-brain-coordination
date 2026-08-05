"""Format adapters make ownership explicit; they do not interpret market or private data."""

from __future__ import annotations

import json
from typing import Iterable

from .evidence import SourceEvidence
from .ledger import FinalizedLedger, LedgerBuilder, SpanOwner


class AdapterError(ValueError):
    pass


def _line_spans(evidence: SourceEvidence) -> Iterable[tuple[int, int, bytes]]:
    for line in evidence.index.line_records:
        if line.start != line.end:
            yield line.start, line.end, evidence.bytes_slice(line.start, line.end)


def build_ledger(evidence: SourceEvidence) -> FinalizedLedger:
    """Create a total ledger using only exact input bytes and declared public format."""
    format_name = evidence.identity["format"]
    builder = LedgerBuilder(evidence)
    if evidence.byte_length == 0:
        raise AdapterError("empty sources have no atomizable public bytes")
    if format_name == "json":
        try:
            json.loads(evidence.text_slice(0, evidence.byte_length))
        except json.JSONDecodeError as exc:
            raise AdapterError("json source is structurally invalid") from exc
        builder.add(0, evidence.byte_length, SpanOwner.ATOM_CANDIDATE)
    elif format_name == "jsonl":
        for start, end, raw in _line_spans(evidence):
            text = raw.decode("utf-8", "strict").strip()
            owner = SpanOwner.STRUCTURAL if not text else SpanOwner.ATOM_CANDIDATE
            if text:
                try:
                    json.loads(text)
                except json.JSONDecodeError as exc:
                    raise AdapterError("jsonl line is structurally invalid") from exc
            builder.add(start, end, owner)
    elif format_name == "markdown":
        for start, end, raw in _line_spans(evidence):
            stripped = raw.strip()
            if not stripped or stripped.startswith(b"#"):
                owner = SpanOwner.STRUCTURAL
            elif stripped == b"[REDACTED]":
                owner = SpanOwner.REDACTED
            else:
                owner = SpanOwner.ATOM_CANDIDATE
            builder.add(start, end, owner)
    else:
        for start, end, raw in _line_spans(evidence):
            owner = SpanOwner.STRUCTURAL if raw.strip() == b"" else SpanOwner.ATOM_CANDIDATE
            builder.add(start, end, owner)
    return builder.finalize()
