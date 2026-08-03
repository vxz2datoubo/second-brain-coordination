"""Durable, revisioned claim authority for E41 engineering tests.

The authority is deliberately separated from ``MetadataStore``: the latter is
local audit state, while this module requires an externally revisioned object
gateway.  E41 provides a synthetic file-backed gateway only for deterministic
tests; it does not perform a live GitHub, App, or CLI operation.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import timedelta
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Iterator, Protocol

from .models import ValidationError, canonical_hash, parse_rfc3339_utc, require_identifier, strict_json_loads


_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_REVISION = re.compile(r"^[0-9a-f]{40,64}$")
_GIT_REF = re.compile(r"^refs/heads/[A-Za-z0-9_.-]+$")


class DurableClaimState(str, Enum):
    CLAIMED = "CLAIMED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"

    @property
    def terminal(self) -> bool:
        return self is not DurableClaimState.CLAIMED


class DurableClaimResultCode(str, Enum):
    CLAIMED = "CLAIMED"
    FINALIZED = "FINALIZED"
    INVOCATION_ATTACHED = "INVOCATION_ATTACHED"
    DUPLICATE_INVOCATION = "DUPLICATE_INVOCATION"
    INVOCATION_MISMATCH = "INVOCATION_MISMATCH"
    ALREADY_CLAIMED = "ALREADY_CLAIMED"
    TERMINAL_EXISTS = "TERMINAL_EXISTS"
    CAS_CONFLICT = "CAS_CONFLICT"
    AUTHORITY_UNAVAILABLE = "AUTHORITY_UNAVAILABLE"
    CLAIM_NOT_FOUND = "CLAIM_NOT_FOUND"
    CLAIM_OWNER_MISMATCH = "CLAIM_OWNER_MISMATCH"


@dataclass(frozen=True)
class DurableClaimKey:
    repository: str
    route_id: str
    route_epoch: int
    task_id: str
    canary_id: str
    nonce: str

    def __post_init__(self) -> None:
        if not isinstance(self.repository, str) or _REPOSITORY.fullmatch(self.repository) is None:
            raise ValidationError("durable claim repository must be owner/name")
        for value, label in (
            (self.route_id, "durable claim route_id"),
            (self.task_id, "durable claim task_id"),
            (self.canary_id, "durable claim canary_id"),
            (self.nonce, "durable claim nonce"),
        ):
            require_identifier(value, label)
        if not isinstance(self.route_epoch, int) or self.route_epoch < 0:
            raise ValidationError("durable claim route_epoch must be non-negative")

    @property
    def storage_id(self) -> str:
        return canonical_hash(
            {
                "repository": self.repository,
                "route_id": self.route_id,
                "route_epoch": self.route_epoch,
                "task_id": self.task_id,
                "canary_id": self.canary_id,
                "nonce": self.nonce,
            }
        )


@dataclass(frozen=True)
class DurableClaimRecord:
    key: DurableClaimKey
    claim_id: str
    owner_type: str
    parent_correlation_id: str
    state: DurableClaimState
    claimed_at: str
    terminal_at: str | None = None
    terminal_reason: str | None = None
    invocation_id: str | None = None

    def __post_init__(self) -> None:
        require_identifier(self.claim_id, "durable claim_id")
        require_identifier(self.owner_type, "durable owner_type")
        require_identifier(self.parent_correlation_id, "durable parent_correlation_id")
        parse_rfc3339_utc(self.claimed_at, "durable claimed_at")
        if self.state.terminal:
            if self.terminal_at is None or self.terminal_reason is None:
                raise ValidationError("terminal durable record requires time and reason")
            parse_rfc3339_utc(self.terminal_at, "durable terminal_at")
            require_identifier(self.terminal_reason, "durable terminal_reason")
        elif self.terminal_at is not None or self.terminal_reason is not None:
            raise ValidationError("claimed durable record cannot carry a terminal outcome")
        if self.invocation_id is not None:
            require_identifier(self.invocation_id, "durable invocation_id")

    def document(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "key": {
                "repository": self.key.repository,
                "route_id": self.key.route_id,
                "route_epoch": self.key.route_epoch,
                "task_id": self.key.task_id,
                "canary_id": self.key.canary_id,
                "nonce": self.key.nonce,
            },
            "claim_id": self.claim_id,
            "owner_type": self.owner_type,
            "parent_correlation_id": self.parent_correlation_id,
            "state": self.state.value,
            "claimed_at": self.claimed_at,
            "terminal_at": self.terminal_at,
            "terminal_reason": self.terminal_reason,
            "invocation_id": self.invocation_id,
        }

    @property
    def document_bytes(self) -> bytes:
        return json.dumps(self.document(), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_document_bytes(cls, payload: bytes) -> "DurableClaimRecord":
        try:
            value = strict_json_loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, ValidationError) as exc:
            raise ValidationError("durable claim document invalid") from exc
        if not isinstance(value, dict) or value.get("schema_version") != "1.0":
            raise ValidationError("durable claim document schema unsupported")
        key = value.get("key")
        if not isinstance(key, dict):
            raise ValidationError("durable claim document key missing")
        try:
            return cls(
                key=DurableClaimKey(
                    repository=key["repository"],
                    route_id=key["route_id"],
                    route_epoch=key["route_epoch"],
                    task_id=key["task_id"],
                    canary_id=key["canary_id"],
                    nonce=key["nonce"],
                ),
                claim_id=value["claim_id"],
                owner_type=value["owner_type"],
                parent_correlation_id=value["parent_correlation_id"],
                state=DurableClaimState(value["state"]),
                claimed_at=value["claimed_at"],
                terminal_at=value.get("terminal_at"),
                terminal_reason=value.get("terminal_reason"),
                invocation_id=value.get("invocation_id"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("durable claim document field invalid") from exc


@dataclass(frozen=True)
class RevisionedObject:
    """A payload plus the opaque revision used by a CAS authority.

    GitHub Contents exposes a Git blob SHA (normally SHA-1) while the
    synthetic gateway uses a SHA-256 payload digest.  Treating the revision
    as opaque preserves either implementation's compare-and-set token; the
    separately verified payload digest retains content integrity.
    """

    revision: str | None
    payload: bytes | None
    payload_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.revision is None:
            if self.payload is not None or self.payload_sha256 is not None:
                raise ValidationError("missing durable revision cannot carry payload")
        else:
            if _REVISION.fullmatch(self.revision) is None or self.payload is None:
                raise ValidationError("durable object revision/payload mismatch")
            expected = hashlib.sha256(self.payload).hexdigest()
            if self.payload_sha256 is not None and self.payload_sha256 != expected:
                raise ValidationError("durable object payload digest mismatch")
            object.__setattr__(self, "payload_sha256", expected)


@dataclass(frozen=True)
class CasWriteResult:
    applied: bool
    revision: str | None


class RevisionedObjectGateway(Protocol):
    """A fixed-repository CAS surface; implementations expose no generic write."""

    def read(self, object_id: str) -> RevisionedObject: ...

    def compare_and_set(self, object_id: str, expected_revision: str | None, payload: bytes) -> CasWriteResult: ...


class FixedRepositoryContentCasClient(Protocol):
    """Minimal injected client for a fixed-repository GitHub Contents CAS.

    A runtime adapter may satisfy this protocol with GitHub's conditional
    content update semantics.  It receives only a preconfigured repository,
    ref, and path; credential acquisition and arbitrary repository writes are
    intentionally outside this module.
    """

    def read_content(self, repository: str, ref: str, path: str) -> RevisionedObject: ...

    def compare_and_set_content(
        self,
        repository: str,
        ref: str,
        path: str,
        expected_revision: str | None,
        payload: bytes,
    ) -> CasWriteResult: ...


class FixedRepositoryGitHubCasGateway:
    """Map claim objects onto one fixed repository/ref/path prefix.

    This is a boundary contract, not a live API client.  A caller must inject
    a constrained Contents/ref CAS client and cannot retarget the repository
    per operation.  E41 tests use only :class:`SyntheticFileCasGateway`.
    """

    def __init__(
        self,
        repository: str,
        ref: str,
        path_prefix: str,
        client: FixedRepositoryContentCasClient,
    ) -> None:
        if _REPOSITORY.fullmatch(repository) is None:
            raise ValidationError("fixed GitHub CAS repository must be owner/name")
        if not isinstance(ref, str) or _GIT_REF.fullmatch(ref) is None:
            raise ValidationError("fixed GitHub CAS ref must be refs/heads/name")
        if not isinstance(path_prefix, str) or not path_prefix or path_prefix.startswith("/") or ".." in path_prefix.split("/"):
            raise ValidationError("fixed GitHub CAS path prefix invalid")
        self._repository = repository
        self._ref = ref
        self._path_prefix = path_prefix.rstrip("/")
        self._client = client

    def _path(self, object_id: str) -> str:
        require_identifier(object_id, "durable object_id")
        return f"{self._path_prefix}/{object_id}.json"

    def read(self, object_id: str) -> RevisionedObject:
        return self._client.read_content(self._repository, self._ref, self._path(object_id))

    def compare_and_set(self, object_id: str, expected_revision: str | None, payload: bytes) -> CasWriteResult:
        return self._client.compare_and_set_content(
            self._repository,
            self._ref,
            self._path(object_id),
            expected_revision,
            payload,
        )


@dataclass(frozen=True)
class DurableClaimResult:
    code: DurableClaimResultCode
    record: DurableClaimRecord | None


class DurableClaimAuthority:
    """Repository-bound durable authority using a revisioned object gateway."""

    def __init__(self, repository: str, namespace: str, gateway: RevisionedObjectGateway) -> None:
        if not isinstance(repository, str) or _REPOSITORY.fullmatch(repository) is None:
            raise ValidationError("durable authority repository must be owner/name")
        require_identifier(namespace, "durable authority namespace")
        self._repository = repository
        self._namespace = namespace
        self._gateway = gateway

    def _object_id(self, key: DurableClaimKey) -> str:
        if key.repository != self._repository:
            raise ValidationError("durable key repository mismatch")
        return f"{self._namespace}.{key.storage_id}"

    def read(self, key: DurableClaimKey) -> DurableClaimRecord | None:
        object_id = self._object_id(key)
        snapshot = self._gateway.read(object_id)
        if snapshot.payload is None:
            return None
        record = DurableClaimRecord.from_document_bytes(snapshot.payload)
        if record.key != key:
            raise ValidationError("durable object key substitution")
        return record

    def claim(self, key: DurableClaimKey, claim_id: str, owner_type: str, parent_correlation_id: str, claimed_at: str) -> DurableClaimResult:
        parse_rfc3339_utc(claimed_at, "durable claim time")
        proposed = DurableClaimRecord(key, claim_id, owner_type, parent_correlation_id, DurableClaimState.CLAIMED, claimed_at)
        object_id = self._object_id(key)
        try:
            snapshot = self._gateway.read(object_id)
        except OSError:
            return DurableClaimResult(DurableClaimResultCode.AUTHORITY_UNAVAILABLE, None)
        if snapshot.payload is not None:
            existing = DurableClaimRecord.from_document_bytes(snapshot.payload)
            return DurableClaimResult(
                DurableClaimResultCode.TERMINAL_EXISTS if existing.state.terminal else DurableClaimResultCode.ALREADY_CLAIMED,
                existing,
            )
        try:
            result = self._gateway.compare_and_set(object_id, None, proposed.document_bytes)
        except OSError:
            return DurableClaimResult(DurableClaimResultCode.AUTHORITY_UNAVAILABLE, None)
        if result.applied:
            return DurableClaimResult(DurableClaimResultCode.CLAIMED, proposed)
        observed = self.read(key)
        if observed is None:
            return DurableClaimResult(DurableClaimResultCode.CAS_CONFLICT, None)
        return DurableClaimResult(
            DurableClaimResultCode.TERMINAL_EXISTS if observed.state.terminal else DurableClaimResultCode.ALREADY_CLAIMED,
            observed,
        )

    def finalize(
        self,
        key: DurableClaimKey,
        claim_id: str,
        state: DurableClaimState,
        terminal_reason: str,
        terminal_at: str,
        *,
        invocation_id: str | None = None,
    ) -> DurableClaimResult:
        if not state.terminal:
            raise ValidationError("durable finalization requires a terminal state")
        parse_rfc3339_utc(terminal_at, "durable terminal time")
        require_identifier(terminal_reason, "durable terminal reason")
        object_id = self._object_id(key)
        try:
            snapshot = self._gateway.read(object_id)
        except OSError:
            return DurableClaimResult(DurableClaimResultCode.AUTHORITY_UNAVAILABLE, None)
        if snapshot.payload is None:
            return DurableClaimResult(DurableClaimResultCode.CLAIM_NOT_FOUND, None)
        current = DurableClaimRecord.from_document_bytes(snapshot.payload)
        if current.claim_id != claim_id:
            return DurableClaimResult(DurableClaimResultCode.CLAIM_OWNER_MISMATCH, current)
        if current.state.terminal:
            return DurableClaimResult(DurableClaimResultCode.TERMINAL_EXISTS, current)
        if current.invocation_id is not None:
            if invocation_id is not None and invocation_id != current.invocation_id:
                return DurableClaimResult(DurableClaimResultCode.INVOCATION_MISMATCH, current)
            invocation_id = current.invocation_id
        terminal = replace(
            current,
            state=state,
            terminal_at=terminal_at,
            terminal_reason=terminal_reason,
            invocation_id=invocation_id,
        )
        try:
            result = self._gateway.compare_and_set(object_id, snapshot.revision, terminal.document_bytes)
        except OSError:
            return DurableClaimResult(DurableClaimResultCode.AUTHORITY_UNAVAILABLE, current)
        if result.applied:
            return DurableClaimResult(DurableClaimResultCode.FINALIZED, terminal)
        observed = self.read(key)
        return DurableClaimResult(DurableClaimResultCode.TERMINAL_EXISTS if observed else DurableClaimResultCode.CAS_CONFLICT, observed)

    def attach_invocation(self, key: DurableClaimKey, claim_id: str, invocation_id: str) -> DurableClaimResult:
        """Durably bind one observed invocation before accepting its receipt.

        The method does not dispatch anything.  It makes duplicate callbacks
        and a second owner observable as either a duplicate or a mismatch
        rather than silently accepting a replacement invocation ID.
        """

        require_identifier(invocation_id, "durable invocation_id")
        object_id = self._object_id(key)
        try:
            snapshot = self._gateway.read(object_id)
        except OSError:
            return DurableClaimResult(DurableClaimResultCode.AUTHORITY_UNAVAILABLE, None)
        if snapshot.payload is None:
            return DurableClaimResult(DurableClaimResultCode.CLAIM_NOT_FOUND, None)
        current = DurableClaimRecord.from_document_bytes(snapshot.payload)
        if current.claim_id != claim_id:
            return DurableClaimResult(DurableClaimResultCode.CLAIM_OWNER_MISMATCH, current)
        if current.state.terminal:
            return DurableClaimResult(DurableClaimResultCode.TERMINAL_EXISTS, current)
        if current.invocation_id is not None:
            return DurableClaimResult(
                DurableClaimResultCode.DUPLICATE_INVOCATION
                if current.invocation_id == invocation_id
                else DurableClaimResultCode.INVOCATION_MISMATCH,
                current,
            )
        updated = replace(current, invocation_id=invocation_id)
        try:
            result = self._gateway.compare_and_set(object_id, snapshot.revision, updated.document_bytes)
        except OSError:
            return DurableClaimResult(DurableClaimResultCode.AUTHORITY_UNAVAILABLE, current)
        if result.applied:
            return DurableClaimResult(DurableClaimResultCode.INVOCATION_ATTACHED, updated)
        observed = self.read(key)
        if observed is None:
            return DurableClaimResult(DurableClaimResultCode.CAS_CONFLICT, None)
        if observed.invocation_id == invocation_id:
            return DurableClaimResult(DurableClaimResultCode.DUPLICATE_INVOCATION, observed)
        return DurableClaimResult(DurableClaimResultCode.INVOCATION_MISMATCH, observed)

    def recover_expired_claim(self, key: DurableClaimKey, observed_at: str, timeout_seconds: int) -> DurableClaimResult:
        if not isinstance(timeout_seconds, int) or timeout_seconds < 1:
            raise ValidationError("durable claim timeout must be positive")
        observed = parse_rfc3339_utc(observed_at, "durable recovery observation")
        current = self.read(key)
        if current is None:
            return DurableClaimResult(DurableClaimResultCode.CLAIM_NOT_FOUND, None)
        if current.state.terminal:
            return DurableClaimResult(DurableClaimResultCode.TERMINAL_EXISTS, current)
        if observed < parse_rfc3339_utc(current.claimed_at, "durable claimed_at") + timedelta(seconds=timeout_seconds):
            return DurableClaimResult(DurableClaimResultCode.ALREADY_CLAIMED, current)
        return self.finalize(
            key,
            current.claim_id,
            DurableClaimState.RECOVERY_REQUIRED,
            "claim_timeout_requires_manual_reconciliation",
            observed_at,
        )


class SyntheticFileCasGateway:
    """A test-only durable CAS gateway with atomic create/replace and a lease lock.

    It models the compare-and-swap contract that a fixed-repository GitHub
    contents/ref client must provide.  It is not a production GitHub adapter.
    """

    def __init__(self, root: Path, *, lock_timeout_seconds: float = 3.0) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        if not isinstance(lock_timeout_seconds, (int, float)) or lock_timeout_seconds <= 0:
            raise ValidationError("synthetic CAS lock timeout must be positive")
        self._lock_timeout_seconds = float(lock_timeout_seconds)

    def _path(self, object_id: str) -> Path:
        require_identifier(object_id, "durable object_id")
        return self._root / f"{object_id}.json"

    def read(self, object_id: str) -> RevisionedObject:
        path = self._path(object_id)
        if not path.exists():
            return RevisionedObject(None, None)
        payload = path.read_bytes()
        return RevisionedObject(hashlib.sha256(payload).hexdigest(), payload)

    @contextmanager
    def _lock(self, object_id: str) -> Iterator[None]:
        lock_path = self._root / f"{object_id}.lock"
        deadline = time.monotonic() + self._lock_timeout_seconds
        descriptor: int | None = None
        while descriptor is None:
            try:
                descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise OSError("synthetic_cas_lock_timeout")
                time.sleep(0.005)
        try:
            yield
        finally:
            os.close(descriptor)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def compare_and_set(self, object_id: str, expected_revision: str | None, payload: bytes) -> CasWriteResult:
        if not isinstance(payload, bytes) or not payload:
            raise ValidationError("durable CAS payload must be nonempty bytes")
        if expected_revision is not None and _REVISION.fullmatch(expected_revision) is None:
            raise ValidationError("durable CAS expected revision invalid")
        path = self._path(object_id)
        with self._lock(object_id):
            current = self.read(object_id)
            if current.revision != expected_revision:
                return CasWriteResult(False, current.revision)
            descriptor, temporary = tempfile.mkstemp(prefix=f"{object_id}.", suffix=".tmp", dir=self._root)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            return CasWriteResult(True, hashlib.sha256(payload).hexdigest())
