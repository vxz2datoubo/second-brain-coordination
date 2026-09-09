"""B1 — RFC8785/JCS-compatible canonical JSON serialization + SHA-256 hash chain.

This module provides a deterministic byte-level canonicalization of JSON values
following the spirit of RFC 8785 (JSON Canonicalization Scheme / JCS):

- object keys sorted in ascending UTF-16 code-unit order (lexicographic for ASCII);
- no insignificant whitespace;
- minimal string escaping (only what JSON requires), UTF-8 output;
- numbers serialized in a stable, ECMAScript-compatible way (integers exactly;
  non-integers via a deterministic decimal formatter).

Because monetary/credit values in this kernel are always carried as *scaled
integers* (see Evidence Contract "Decimal/scaled-integer semantics"), the number
formatter avoids floating-point ambiguity in the hot path.
"""

from __future__ import annotations

import json
import math
from typing import Any


def _jcs_escape(s: str) -> str:
    """Minimal JSON string escaping producing the same bytes as RFC 8785 for our inputs."""
    out = []
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif o < 0x20:
            out.append("\\u%04x" % o)
        else:
            out.append(ch)
    return "".join(out)


def _jcs_number(n: Any) -> str:
    """ECMAScript-compatible number serialization (deterministic)."""
    if isinstance(n, bool):
        # bool is a subclass of int; handle explicitly.
        return "true" if n else "false"
    if isinstance(n, int):
        return str(n)
    if isinstance(n, float):
        if math.isnan(n) or math.isinf(n):
            raise ValueError("RFC8785 canonical JSON forbids NaN/Infinity")
        if n == int(n) and abs(n) < 1e16:
            # integral float -> integer form, matching ECMAScript Number.toString
            return str(int(n))
        # deterministic repr with ECMAScript-compatible exponent where needed
        r = repr(n)
        if "e" in r:
            mant, _, exp = r.partition("e")
            exp = int(exp)
            mant = mant.replace(".", "")
            sign = ""
            if exp < 0:
                sign = "-"
                exp = -exp
            return f"{mant}e{sign}{exp}"
        return r
    raise TypeError(f"non-JSON number type: {type(n)!r}")


def jcs_dumps(value: Any) -> str:
    """Serialize ``value`` to a canonical JSON string (RFC 8785 spirit)."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return _jcs_number(value)
    if isinstance(value, str):
        return '"' + _jcs_escape(value) + '"'
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(jcs_dumps(item) for item in value) + "]"
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda kv: kv[0])
        return "{" + ",".join(
            '"' + _jcs_escape(str(k)) + '":' + jcs_dumps(v) for k, v in items
        ) + "}"
    raise TypeError(f"cannot canonically serialize type: {type(value)!r}")


def jcs_bytes(value: Any) -> bytes:
    """Return UTF-8 canonical bytes for ``value``."""
    return jcs_dumps(value).encode("utf-8")


def canonical_dumps(value: Any) -> str:
    """Backwards-friendly alias for :func:`jcs_dumps`."""
    return jcs_dumps(value)


# ---------------------------------------------------------------------------
# SHA-256 event hash chain (B1)
# ---------------------------------------------------------------------------
import hashlib  # noqa: E402

GENESIS_PREVIOUS_HASH = "0" * 64  # explicit genesis / no-previous marker


def event_hash(previous_event_hash: str, *, mission_id: str, run_id: str,
               state_seq: int, event_type: str, actor: str, timestamp_iso: str,
               payload: Any, digests: dict | None = None) -> str:
    """Compute the deterministic SHA-256 hash of an event envelope.

    The hash covers every field *except* ``event_hash`` itself, and binds the
    previous event's hash, so the chain is append-only and tamper-evident.
    """
    envelope = {
        "mission_id": mission_id,
        "run_id": run_id,
        "state_seq": state_seq,
        "event_type": event_type,
        "previous_event_hash": previous_event_hash,
        "actor": actor,
        "timestamp_iso": timestamp_iso,
        "payload": payload,
        "digests": digests if digests is not None else {},
    }
    return hashlib.sha256(jcs_bytes(envelope)).hexdigest()


def payload_digest(payload: Any) -> str:
    """SHA-256 of a payload's canonical bytes, for independent content verification."""
    return hashlib.sha256(jcs_bytes(payload)).hexdigest()


def content_sha256(raw_bytes: bytes) -> str:
    """SHA-256 hex digest of arbitrary bytes (used for artifact/fixture verification)."""
    return hashlib.sha256(raw_bytes).hexdigest()
