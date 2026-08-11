"""Deterministic bounded public corpus and minimized parser counterexamples."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True, slots=True)
class CorpusCase:
    case_id: str
    format_name: str
    payload: bytes
    accepted: bool
    reason: str


def fixed_corpus() -> tuple[CorpusCase, ...]:
    return (
        CorpusCase("valid-text", "text", b"alpha\nbeta\n", True, "two UTF-8 claim lines"),
        CorpusCase("blank-text", "text", b"\n", True, "structural blank line"),
        CorpusCase("invalid-utf8-ed", "text", b"\xed", False, "minimal invalid UTF-8 leading byte"),
        CorpusCase("truncated-utf8", "text", b"\xe4\xb8", False, "truncated multibyte sequence"),
        CorpusCase("valid-json", "json", b'{"claim":"alpha"}', True, "one JSON source"),
        CorpusCase("invalid-json", "json", b'{"claim":', False, "minimal incomplete JSON"),
        CorpusCase("valid-jsonl", "jsonl", b'{"a":1}\n{"b":2}\n', True, "two JSON lines"),
        CorpusCase("invalid-jsonl", "jsonl", b'{"a":1}\n{', False, "invalid final JSONL line"),
        CorpusCase("nonempty-unknown-format", "csv", b"a,b\n", False, "unsupported declared format"),
    )


def corpus_digest(cases: tuple[CorpusCase, ...] | None = None) -> str:
    cases = cases or fixed_corpus()
    body = [
        {"case_id": item.case_id, "format_name": item.format_name, "payload_hex": item.payload.hex(), "accepted": item.accepted, "reason": item.reason}
        for item in cases
    ]
    return sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
