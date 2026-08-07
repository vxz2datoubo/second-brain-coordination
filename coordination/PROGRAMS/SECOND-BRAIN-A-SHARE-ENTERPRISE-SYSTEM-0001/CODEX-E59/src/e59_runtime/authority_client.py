"""Client-side canonical authority boundary for E59 synthetic verification."""

from __future__ import annotations

from dataclasses import dataclass
import base64
from hashlib import sha256
import json
import os
from pathlib import Path
from secrets import token_hex
import socket
import sys
import tempfile
import time
from typing import Any

from .process_tree import OwnedProcessTree, ProcessLifecycleError, ResourceGate


class AuthorityError(ValueError):
    """The synthetic authority rejected a candidate or connection."""


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


@dataclass(frozen=True, slots=True)
class Proposition:
    subject: str
    predicate: str
    object_value: str
    polarity: str
    scope: str
    time_window: str

    def as_dict(self) -> dict[str, str]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object_value": self.object_value,
            "polarity": self.polarity,
            "scope": self.scope,
            "time_window": self.time_window,
        }


@dataclass(frozen=True, slots=True)
class AuthorityDescriptor:
    protocol_version: str
    authority_id: str
    host_pid: int
    host_port: int
    session_fingerprint: str
    descriptor_digest: str


@dataclass(frozen=True, slots=True)
class AuthorityAnchor:
    authority_id: str
    descriptor_digest: str
    protocol_version: str


def _descriptor(value: object) -> AuthorityDescriptor:
    if not isinstance(value, dict):
        raise AuthorityError("AUTHORITY_DESCRIPTOR_MALFORMED")
    try:
        descriptor = AuthorityDescriptor(
            protocol_version=str(value["protocol_version"]),
            authority_id=str(value["authority_id"]),
            host_pid=int(value["host_pid"]),
            host_port=int(value["host_port"]),
            session_fingerprint=str(value["session_fingerprint"]),
            descriptor_digest=str(value["descriptor_digest"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthorityError("AUTHORITY_DESCRIPTOR_MALFORMED") from exc
    claim = {
        "protocol_version": descriptor.protocol_version,
        "authority_id": descriptor.authority_id,
        "host_pid": descriptor.host_pid,
        "host_port": descriptor.host_port,
        "session_fingerprint": descriptor.session_fingerprint,
    }
    if sha256(_canonical(claim)).hexdigest() != descriptor.descriptor_digest:
        raise AuthorityError("AUTHORITY_DESCRIPTOR_DIGEST_MISMATCH")
    return descriptor


class CanonicalVerifier:
    """Verifier consumer; it cannot issue source, evidence, or relation records."""

    __slots__ = ("_descriptor", "_anchor", "_token")

    def __init__(self, descriptor: AuthorityDescriptor, anchor: AuthorityAnchor, token: str, *, _factory_marker: object | None = None) -> None:
        if _factory_marker is not _FACTORY_MARKER:
            raise AuthorityError("CANONICAL_VERIFIER_REQUIRES_AUTHORITY_FACTORY")
        self._descriptor = descriptor
        self._anchor = anchor
        self._token = token

    def _request(self, operation: str, **payload: object) -> dict[str, object]:
        request = {"operation": operation, "session_token": self._token, **payload}
        try:
            with socket.create_connection(("127.0.0.1", self._descriptor.host_port), timeout=5) as connection:
                connection.sendall(_canonical(request) + b"\n")
                response = bytearray()
                while not response.endswith(b"\n"):
                    chunk = connection.recv(65536)
                    if not chunk:
                        raise AuthorityError("AUTHORITY_RESPONSE_TRUNCATED")
                    response.extend(chunk)
        except OSError as exc:
            raise AuthorityError("CANONICAL_AUTHORITY_UNAVAILABLE") from exc
        value = json.loads(bytes(response[:-1]).decode("utf-8", "strict"))
        if not isinstance(value, dict) or not value.get("ok"):
            raise AuthorityError(str(value.get("error", "AUTHORITY_REJECTED")) if isinstance(value, dict) else "AUTHORITY_RESPONSE_MALFORMED")
        if operation != "describe":
            descriptor = self._request("describe")["descriptor"]
            current = _descriptor(descriptor)
            if (
                current.authority_id != self._anchor.authority_id
                or current.descriptor_digest != self._anchor.descriptor_digest
                or current.protocol_version != self._anchor.protocol_version
            ):
                raise AuthorityError("CANONICAL_AUTHORITY_ANCHOR_MISMATCH")
        return value

    def verify_evidence(self, evidence: object) -> bool:
        try:
            return bool(self._request("verify_evidence", evidence=evidence).get("verified"))
        except AuthorityError:
            return False

    def verify_relation(self, relation: object) -> bool:
        try:
            return bool(self._request("verify_relation", relation=relation).get("verified"))
        except AuthorityError:
            return False


_FACTORY_MARKER = object()


class _SemanticIssuer:
    """Harness-only issuer; it is not re-exported by the public package."""

    def __init__(self, verifier: CanonicalVerifier) -> None:
        self._verifier = verifier

    def admit_source(self, raw: bytes) -> dict[str, object]:
        return dict(self._verifier._request("admit_source", raw_b64=base64.b64encode(raw).decode("ascii"))["source"])

    def issue_span(self, source: dict[str, object], start: int, end: int) -> dict[str, object]:
        return dict(self._verifier._request("issue_span", source_id=source["source_id"], start=start, end=end)["span"])

    def validate_evidence(self, source: dict[str, object], span: dict[str, object], proposition: Proposition, excerpt_hint: str) -> dict[str, object]:
        return dict(
            self._verifier._request(
                "validate_evidence",
                source_id=source["source_id"],
                span_id=span["span_id"],
                proposition=proposition.as_dict(),
                excerpt_hint=excerpt_hint,
            )["evidence"]
        )

    def derive_relation(self, left: dict[str, object], right: dict[str, object], relation_hint: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {"left": left, "right": right}
        if relation_hint is not None:
            payload["relation_hint"] = relation_hint
        return dict(self._verifier._request("derive_relation", **payload)["relation"])


class _SyntheticAuthorityHarness:
    """Test-only, bounded launcher for one short-lived authority host."""

    def __init__(self) -> None:
        self._token = token_hex(32)
        self._temporary = tempfile.TemporaryDirectory(prefix="e59-authority-")
        self._ready_file = Path(self._temporary.name) / "descriptor.json"
        self._gate = ResourceGate("E59-canonical-authority", max_task_processes=2, max_shared_processes=8)
        self._tree = OwnedProcessTree("E59-canonical-authority", gate=self._gate)
        self.descriptor: AuthorityDescriptor | None = None
        self.anchor: AuthorityAnchor | None = None
        self.verifier: CanonicalVerifier | None = None
        self.issuer: _SemanticIssuer | None = None

    def start(self) -> "_SyntheticAuthorityHarness":
        self._gate.acquire()
        environment = dict(os.environ)
        environment["E59_AUTHORITY_SESSION_TOKEN"] = self._token
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
        command = [sys.executable, "-m", "e59_runtime.authority_host", "--ready-file", str(self._ready_file)]
        self._tree.spawn(command, purpose="canonical-authority-host", env=environment)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self._ready_file.exists():
                self.descriptor = _descriptor(json.loads(self._ready_file.read_text(encoding="utf-8")))
                self.anchor = AuthorityAnchor(
                    authority_id=self.descriptor.authority_id,
                    descriptor_digest=self.descriptor.descriptor_digest,
                    protocol_version=self.descriptor.protocol_version,
                )
                self.verifier = CanonicalVerifier(self.descriptor, self.anchor, self._token, _factory_marker=_FACTORY_MARKER)
                self.issuer = _SemanticIssuer(self.verifier)
                return self
            time.sleep(0.02)
        self.close()
        raise AuthorityError("CANONICAL_AUTHORITY_START_TIMEOUT")

    def close(self) -> None:
        try:
            if self.verifier is not None:
                try:
                    self.verifier._request("shutdown")
                except AuthorityError:
                    pass
            self._tree.cleanup("authority_harness_close")
        finally:
            self._gate.release()
            self._temporary.cleanup()

    def __enter__(self) -> "_SyntheticAuthorityHarness":
        return self.start()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
