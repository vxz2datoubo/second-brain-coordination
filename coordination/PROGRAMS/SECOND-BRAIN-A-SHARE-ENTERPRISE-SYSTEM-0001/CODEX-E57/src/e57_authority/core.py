"""Isolated issuer and non-forgeable-by-normal-import record handles.

The child process owns the attestation key and issued-wire ledger. The parent
keeps a presentation permit for the exact object returned by an AuthoritySession
so value clones are rejected even if their public fields match. Python cannot
hide an object from hostile code with arbitrary reflection or process control;
that adversary is explicitly outside this narrow service-boundary claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import hmac
import json
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection, wait
from secrets import token_bytes
from types import MappingProxyType
from typing import Any, Mapping


class AuthorityError(ValueError):
    """Raised when a public-safe E57 authority invariant fails."""


class RecordKind(str, Enum):
    SOURCE = "SOURCE"
    ATOM = "ATOM"
    EVIDENCE = "EVIDENCE"
    PACKET = "PACKET"
    RELATION = "RELATION"


def _normalise(value: object) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Mapping):
        return {str(key): _normalise(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, tuple | list):
        return [_normalise(item) for item in value]
    raise AuthorityError("value is outside the canonical public JSON domain")


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(_normalise(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AuthorityError("value cannot be canonically encoded") from exc


def stable_digest(value: object) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True, eq=False)
class AuthorityRecord:
    kind: RecordKind
    record_id: str
    issuer_id: str
    payload_json: str
    attestation: str

    def payload(self) -> Mapping[str, object]:
        try:
            value = json.loads(self.payload_json)
        except json.JSONDecodeError as exc:  # defensive: issuer always emits valid JSON
            raise AuthorityError("record payload is not valid canonical JSON") from exc
        if not isinstance(value, dict):
            raise AuthorityError("record payload must be an object")
        return MappingProxyType(value)

    @property
    def payload_digest(self) -> str:
        return sha256(self.payload_json.encode("utf-8")).hexdigest()

    def wire(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "kind": self.kind.value,
                "record_id": self.record_id,
                "issuer_id": self.issuer_id,
                "payload_json": self.payload_json,
                "attestation": self.attestation,
            }
        )


@dataclass(frozen=True, slots=True, eq=False)
class SourceRecord(AuthorityRecord):
    pass


@dataclass(frozen=True, slots=True, eq=False)
class AtomRecord(AuthorityRecord):
    pass


@dataclass(frozen=True, slots=True, eq=False)
class EvidenceRecord(AuthorityRecord):
    pass


@dataclass(frozen=True, slots=True, eq=False)
class PacketRecord(AuthorityRecord):
    pass


@dataclass(frozen=True, slots=True, eq=False)
class RelationRecord(AuthorityRecord):
    pass


_RECORD_CLASSES: Mapping[RecordKind, type[AuthorityRecord]] = MappingProxyType(
    {
        RecordKind.SOURCE: SourceRecord,
        RecordKind.ATOM: AtomRecord,
        RecordKind.EVIDENCE: EvidenceRecord,
        RecordKind.PACKET: PacketRecord,
        RecordKind.RELATION: RelationRecord,
    }
)


def _record_message(kind: str, issuer_id: str, record_id: str, payload_json: str) -> bytes:
    return canonical_bytes({"kind": kind, "issuer_id": issuer_id, "record_id": record_id, "payload_json": payload_json})


def _worker(issuer_connection: Connection, verifier_connection: Connection, issuer_id: str) -> None:
    """Run in a child process; only the issuer channel may issue records."""

    key = token_bytes(32)
    issued: dict[str, dict[str, str]] = {}
    connections = (issuer_connection, verifier_connection)
    try:
        running = True
        while running:
            for connection in wait(connections):
                request = connection.recv()
                action = request.get("action") if isinstance(request, dict) else None
                if action == "shutdown" and connection is issuer_connection:
                    connection.send({"ok": True})
                    running = False
                    continue
                if action == "issue" and connection is issuer_connection:
                    try:
                        kind = RecordKind(str(request["kind"]))
                        payload = _normalise(request["payload"])
                        if not isinstance(payload, dict):
                            raise AuthorityError("record payload must be an object")
                        payload_json = canonical_bytes(payload).decode("utf-8")
                        record_id = stable_digest({"issuer_id": issuer_id, "kind": kind.value, "payload_json": payload_json})
                        message = _record_message(kind.value, issuer_id, record_id, payload_json)
                        attestation = hmac.new(key, message, "sha256").hexdigest()
                        wire = {
                            "kind": kind.value,
                            "record_id": record_id,
                            "issuer_id": issuer_id,
                            "payload_json": payload_json,
                            "attestation": attestation,
                        }
                        issued[record_id] = wire
                        connection.send({"ok": True, "wire": wire})
                    except (AuthorityError, KeyError, TypeError, ValueError) as exc:
                        connection.send({"ok": False, "error": str(exc)})
                    continue
                if action == "verify" and connection is verifier_connection:
                    candidate = request.get("wire")
                    if not isinstance(candidate, dict):
                        connection.send({"ok": True, "valid": False})
                        continue
                    record_id = candidate.get("record_id")
                    expected = issued.get(record_id) if isinstance(record_id, str) else None
                    if expected is None:
                        connection.send({"ok": True, "valid": False})
                        continue
                    valid = hmac.compare_digest(canonical_bytes(expected), canonical_bytes(candidate))
                    connection.send({"ok": True, "valid": valid})
                    continue
                connection.send({"ok": False, "error": "action is not available on this channel"})
    finally:
        issuer_connection.close()
        verifier_connection.close()


def _from_wire(wire: Mapping[str, object]) -> AuthorityRecord:
    try:
        kind = RecordKind(str(wire["kind"]))
        record = _RECORD_CLASSES[kind](
            kind=kind,
            record_id=str(wire["record_id"]),
            issuer_id=str(wire["issuer_id"]),
            payload_json=str(wire["payload_json"]),
            attestation=str(wire["attestation"]),
        )
        record.payload()
        return record
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthorityError("issuer response is malformed") from exc


class AuthoritySession:
    """Trusted issuer capability paired with a verifier-only consumer channel.

    A caller that receives this object is intentionally trusted to request
    issuance. Ordinary consumers should receive records and a verifier facade,
    not the session. The verifier process has no `issue` action on its channel.
    """

    __slots__ = ("_issuer_connection", "_verifier_connection", "_process", "_permits", "_closed")

    def __init__(self, *, issuer_id: str = "e57.synthetic.issuer.v1") -> None:
        if not isinstance(issuer_id, str) or not issuer_id:
            raise AuthorityError("issuer_id must be a nonempty public identifier")
        issuer_parent, issuer_child = Pipe(duplex=True)
        verifier_parent, verifier_child = Pipe(duplex=True)
        process = Process(target=_worker, args=(issuer_child, verifier_child, issuer_id), daemon=True)
        process.start()
        issuer_child.close()
        verifier_child.close()
        self._issuer_connection = issuer_parent
        self._verifier_connection = verifier_parent
        self._process = process
        self._permits: dict[int, str] = {}
        self._closed = False

    def __enter__(self) -> "AuthoritySession":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def _require_open(self) -> None:
        if self._closed or not self._process.is_alive():
            raise AuthorityError("issuer session is closed")

    def issue(self, kind: RecordKind, payload: Mapping[str, object]) -> AuthorityRecord:
        self._require_open()
        if not isinstance(kind, RecordKind):
            raise AuthorityError("record kind must be a RecordKind")
        self._issuer_connection.send({"action": "issue", "kind": kind.value, "payload": dict(payload)})
        response = self._issuer_connection.recv()
        if not isinstance(response, dict) or not response.get("ok"):
            raise AuthorityError(str(response.get("error", "issuer rejected request")) if isinstance(response, dict) else "issuer rejected request")
        record = _from_wire(response["wire"])
        self._permits[id(record)] = stable_digest(record.wire())
        return record

    def issue_source(self, *, source_id: str, source_sha256: str, format_name: str, byte_length: int) -> SourceRecord:
        if not source_id or len(source_sha256) != 64 or byte_length < 0 or not format_name:
            raise AuthorityError("source issuance metadata is invalid")
        record = self.issue(
            RecordKind.SOURCE,
            {"source_id": source_id, "source_sha256": source_sha256, "format": format_name, "byte_length": byte_length},
        )
        if not isinstance(record, SourceRecord):
            raise AuthorityError("issuer returned wrong source record type")
        return record

    def verify(self, record: object) -> bool:
        if self._closed or not isinstance(record, AuthorityRecord):
            return False
        try:
            permit = self._permits.get(id(record))
            if permit != stable_digest(record.wire()):
                return False
            self._verifier_connection.send({"action": "verify", "wire": dict(record.wire())})
            response = self._verifier_connection.recv()
            return bool(isinstance(response, dict) and response.get("ok") and response.get("valid"))
        except (AuthorityError, AttributeError, BrokenPipeError, EOFError, OSError, TypeError, ValueError):
            return False

    def require(self, record: object, kind: RecordKind | None = None) -> AuthorityRecord:
        if not self.verify(record):
            raise AuthorityError("record is not an exact issued presentation from this session")
        assert isinstance(record, AuthorityRecord)
        if kind is not None and record.kind is not kind:
            raise AuthorityError("record kind is not allowed for this operation")
        return record

    def close(self) -> None:
        if self._closed:
            return
        try:
            if self._process.is_alive():
                self._issuer_connection.send({"action": "shutdown"})
                self._issuer_connection.recv()
        except (BrokenPipeError, EOFError, OSError):
            pass
        finally:
            self._issuer_connection.close()
            self._verifier_connection.close()
            self._process.join(timeout=2)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=2)
            self._closed = True
