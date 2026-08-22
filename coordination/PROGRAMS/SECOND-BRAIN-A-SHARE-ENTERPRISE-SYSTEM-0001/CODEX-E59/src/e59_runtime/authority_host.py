"""Private E59 synthetic authority host.

The host owns the signing key and all issuance ledgers. It accepts only local
loopback requests carrying a random per-launch session token supplied through
the child environment. The token is never put in the descriptor or receipt.
"""

from __future__ import annotations

import argparse
import base64
import hmac
from hashlib import sha256
import json
import os
from pathlib import Path
from secrets import token_bytes
import socket
import sys
from typing import Any


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def _digest(value: object) -> str:
    return sha256(_canonical(value)).hexdigest()


class AuthorityLedger:
    """All authority decisions are checked against this host-local ledger."""

    def __init__(self, token: str, descriptor: dict[str, object]) -> None:
        self._token = token
        self._key = token_bytes(32)
        self.descriptor = descriptor
        self.sources: dict[str, dict[str, object]] = {}
        self.spans: dict[str, dict[str, object]] = {}
        self.evidence: dict[str, dict[str, object]] = {}
        self.relations: dict[str, dict[str, object]] = {}

    def _assert_token(self, request: dict[str, object]) -> None:
        supplied = str(request.pop("session_token", ""))
        if not hmac.compare_digest(supplied, self._token):
            raise ValueError("SESSION_AUTHENTICATION_FAILED")

    def _sign(self, value: dict[str, object]) -> str:
        return hmac.new(self._key, _canonical(value), "sha256").hexdigest()

    def _attest(self, value: dict[str, object]) -> dict[str, object]:
        signed = dict(value)
        signed["attestation"] = self._sign(value)
        return signed

    def _verify(self, value: object, ledger: dict[str, dict[str, object]], key: str) -> bool:
        if not isinstance(value, dict):
            return False
        identifier = str(value.get(key, ""))
        stored = ledger.get(identifier)
        if stored is None:
            return False
        claim = dict(value)
        attestation = str(claim.pop("attestation", ""))
        return hmac.compare_digest(_canonical(stored), _canonical(claim)) and hmac.compare_digest(self._sign(claim), attestation)

    @staticmethod
    def _proposition(value: object) -> dict[str, str]:
        if not isinstance(value, dict):
            raise ValueError("PROPOSITION_MUST_BE_OBJECT")
        fields = ("subject", "predicate", "object_value", "polarity", "scope", "time_window")
        result: dict[str, str] = {}
        for field in fields:
            text = str(value.get(field, "")).strip()
            if not text:
                raise ValueError(f"PROPOSITION_{field.upper()}_REQUIRED")
            result[field] = text
        if result["polarity"] not in {"AFFIRM", "DENY"}:
            raise ValueError("PROPOSITION_POLARITY_INVALID")
        return result

    @staticmethod
    def _semantic_key(proposition: dict[str, str]) -> str:
        return _digest({key: proposition[key] for key in ("subject", "predicate", "object_value", "scope", "time_window")})

    def handle(self, request: dict[str, object]) -> dict[str, object]:
        self._assert_token(request)
        operation = str(request.get("operation", ""))
        if operation == "describe":
            return {"ok": True, "descriptor": self.descriptor}
        if operation == "admit_source":
            raw = base64.b64decode(str(request.get("raw_b64", "")), validate=True)
            source_digest = sha256(raw).hexdigest()
            source_id = _digest({"authority_id": self.descriptor["authority_id"], "source_digest": source_digest})
            claim = {
                "source_id": source_id,
                "source_digest": source_digest,
                "byte_length": len(raw),
                "authority_id": self.descriptor["authority_id"],
            }
            # Keep authority-owned raw bytes out of the signed, serializable
            # public capability claim. The ledger may retain bytes locally;
            # callers receive only the exact digest and length boundary.
            self.sources[source_id] = {**claim, "raw": raw}
            return {"ok": True, "source": self._attest(claim)}
        if operation == "issue_span":
            source_id = str(request.get("source_id", ""))
            source = self.sources.get(source_id)
            if source is None:
                raise ValueError("SOURCE_CAPABILITY_NOT_ACCEPTED")
            start, end = int(request.get("start", -1)), int(request.get("end", -1))
            raw = bytes(source["raw"])
            if start < 0 or end <= start or end > len(raw):
                raise ValueError("SPAN_RANGE_INVALID")
            try:
                decoded = raw[start:end].decode("utf-8", "strict")
            except UnicodeDecodeError as exc:
                raise ValueError("SPAN_NOT_STRICT_UTF8_BOUNDARY") from exc
            span_id = _digest({"source_id": source_id, "start": start, "end": end, "bytes_sha256": sha256(raw[start:end]).hexdigest()})
            claim = {
                "span_id": span_id,
                "source_id": source_id,
                "source_digest": str(source["source_digest"]),
                "start": start,
                "end": end,
                "bytes_sha256": sha256(raw[start:end]).hexdigest(),
                "decoded_sha256": sha256(decoded.encode("utf-8")).hexdigest(),
                "decoded_text": decoded,
            }
            self.spans[span_id] = claim
            return {"ok": True, "span": self._attest(claim)}
        if operation == "validate_evidence":
            source_id = str(request.get("source_id", ""))
            span_id = str(request.get("span_id", ""))
            source = self.sources.get(source_id)
            span = self.spans.get(span_id)
            if source is None or span is None or span["source_id"] != source_id:
                raise ValueError("SOURCE_SPAN_CAPABILITY_NOT_ACCEPTED")
            proposition = self._proposition(request.get("proposition"))
            excerpt = str(request.get("excerpt_hint", ""))
            if not hmac.compare_digest(excerpt, str(span["decoded_text"])):
                raise ValueError("EXCERPT_DOES_NOT_MATCH_ACCEPTED_SPAN")
            evidence_id = _digest(
                {
                    "source_id": source_id,
                    "span_id": span_id,
                    "proposition": proposition,
                    "semantic_key": self._semantic_key(proposition),
                }
            )
            claim = {
                "evidence_id": evidence_id,
                "source_id": source_id,
                "span_id": span_id,
                "source_digest": str(source["source_digest"]),
                "proposition": proposition,
                "semantic_key": self._semantic_key(proposition),
                "outcome": "PASS",
                "ontology_version": "e59.relation-ontology/1.0.0",
            }
            self.evidence[evidence_id] = claim
            return {"ok": True, "evidence": self._attest(claim)}
        if operation == "verify_evidence":
            return {"ok": True, "verified": self._verify(request.get("evidence"), self.evidence, "evidence_id")}
        if operation == "derive_relation":
            left = request.get("left")
            right = request.get("right")
            if not self._verify(left, self.evidence, "evidence_id") or not self._verify(right, self.evidence, "evidence_id"):
                raise ValueError("RELATION_REQUIRES_ACCEPTED_EVIDENCE")
            assert isinstance(left, dict) and isinstance(right, dict)
            if left["evidence_id"] == right["evidence_id"]:
                raise ValueError("RELATION_REQUIRES_DISTINCT_EVIDENCE")
            left_proposition = left["proposition"]
            right_proposition = right["proposition"]
            assert isinstance(left_proposition, dict) and isinstance(right_proposition, dict)
            if left["semantic_key"] == right["semantic_key"] and left_proposition["polarity"] != right_proposition["polarity"]:
                relation_type, rule_id = "CONTRADICTS", "same_semantic_key_opposite_polarity"
            elif left["semantic_key"] == right["semantic_key"] and left["source_id"] != right["source_id"]:
                relation_type, rule_id = "CORROBORATES", "same_semantic_key_independent_source"
            elif left_proposition["subject"] == right_proposition["subject"]:
                relation_type, rule_id = "SAME_SUBJECT_CONTEXT", "shared_subject"
            else:
                relation_type, rule_id = "UNRELATED", "no_registered_relation"
            hint = request.get("relation_hint")
            if hint is not None and str(hint) != relation_type:
                raise ValueError("CALLER_RELATION_HINT_CONTRADICTS_DERIVED_ONTOLOGY")
            relation_id = _digest(
                {
                    "left_evidence_id": left["evidence_id"],
                    "right_evidence_id": right["evidence_id"],
                    "relation_type": relation_type,
                    "ontology_version": "e59.relation-ontology/1.0.0",
                }
            )
            claim = {
                "relation_id": relation_id,
                "left_evidence_id": left["evidence_id"],
                "right_evidence_id": right["evidence_id"],
                "relation_type": relation_type,
                "rule_id": rule_id,
                "ontology_version": "e59.relation-ontology/1.0.0",
            }
            self.relations[relation_id] = claim
            return {"ok": True, "relation": self._attest(claim)}
        if operation == "verify_relation":
            return {"ok": True, "verified": self._verify(request.get("relation"), self.relations, "relation_id")}
        if operation == "shutdown":
            return {"ok": True, "shutdown": True}
        raise ValueError("OPERATION_NOT_REGISTERED")


def _send(connection: socket.socket, value: dict[str, object]) -> None:
    connection.sendall(_canonical(value) + b"\n")


def _receive(connection: socket.socket) -> dict[str, object]:
    payload = bytearray()
    while not payload.endswith(b"\n"):
        chunk = connection.recv(65536)
        if not chunk:
            raise ValueError("REQUEST_TRUNCATED")
        payload.extend(chunk)
        if len(payload) > 1_000_000:
            raise ValueError("REQUEST_TOO_LARGE")
    decoded = json.loads(bytes(payload[:-1]).decode("utf-8", "strict"))
    if not isinstance(decoded, dict):
        raise ValueError("REQUEST_MUST_BE_OBJECT")
    return decoded


def serve(ready_file: Path) -> int:
    token = os.environ.get("E59_AUTHORITY_SESSION_TOKEN", "")
    if len(token) < 32:
        return 2
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(0.5)
    address = listener.getsockname()
    descriptor = {
        "protocol_version": "e59.canonical-authority/1.0.0",
        "authority_id": sha256(token.encode("ascii")).hexdigest(),
        "host_pid": os.getpid(),
        "host_port": int(address[1]),
        "session_fingerprint": sha256(token.encode("ascii")).hexdigest()[:24],
    }
    descriptor["descriptor_digest"] = _digest(descriptor)
    ready_file.write_text(json.dumps(descriptor, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    ledger = AuthorityLedger(token, descriptor)
    shutting_down = False
    try:
        while not shutting_down:
            try:
                connection, _ = listener.accept()
            except socket.timeout:
                continue
            with connection:
                connection.settimeout(5)
                try:
                    request = _receive(connection)
                    response = ledger.handle(request)
                    shutting_down = bool(response.get("shutdown"))
                except Exception as exc:  # public-safe error code only
                    response = {"ok": False, "error": str(exc)}
                _send(connection, response)
    finally:
        listener.close()
        ready_file.unlink(missing_ok=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ready-file", required=True)
    arguments = parser.parse_args()
    return serve(Path(arguments.ready_file))


if __name__ == "__main__":
    raise SystemExit(main())
