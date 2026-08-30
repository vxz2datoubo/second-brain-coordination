"""Durable, fail-closed session envelopes for the offline creative runtime.

`CreativeSession/v1` remains the legacy source file.  `CreativeSession/v2`
wraps an identical ledger with an explicit graph/timeline provenance record.
Migration never edits or renames the legacy source; it produces a separate,
atomically written envelope only after semantic replay succeeds.
"""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from .continuity import TimelineViolation, graph_for_ledger, verified_director_input
from .contracts import StoryState, canonical_json
from .ledger import CreativeLedger, LedgerViolation


LEGACY_SCHEMA = "CreativeSession/v1"
SESSION_SCHEMA = "CreativeSession/v2"
LEGACY_FILENAME = "session.json"
V2_DIRECTORY = "saves"
V2_FILENAME = "default.json"
SLOT_DIRECTORY = "slots"
DEFAULT_SLOT = "default"
_SLOT_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}")
LOCK_DIRECTORY = ".creative-runtime-locks"


class SessionViolation(ValueError):
    """Raised when a session cannot be migrated or its provenance is invalid."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_slot(slot: str) -> str:
    """Validate a stable local slot name before it becomes any path segment."""

    if not isinstance(slot, str) or not _SLOT_PATTERN.fullmatch(slot):
        raise SessionViolation("Slot must match [a-z0-9][a-z0-9_-]{0,31}")
    return slot


def legacy_session_path(workspace: Path, slot: str = DEFAULT_SLOT) -> Path:
    normalized = validate_slot(slot)
    if normalized == DEFAULT_SLOT:
        return workspace / LEGACY_FILENAME
    return workspace / SLOT_DIRECTORY / (normalized + ".json")


def v2_session_path(workspace: Path, slot: str = DEFAULT_SLOT) -> Path:
    normalized = validate_slot(slot)
    filename = V2_FILENAME if normalized == DEFAULT_SLOT else normalized + ".json"
    return workspace / V2_DIRECTORY / filename


def atomic_replace_text(path: Path, content: str) -> None:
    """Durably replace a mutable runtime record without partial-file exposure.

    This intentionally uses a sibling temporary path and ``os.replace`` so a
    reader observes either the prior complete JSON file or the new complete
    JSON file.  A stranded temporary file is treated as a fail-closed signal;
    it is never silently overwritten because it may be evidence of a prior
    interrupted local operation.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".replace-tmp")
    if temporary.exists():
        raise SessionViolation("A prior incomplete session replacement temporary file exists")
    created = False
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            created = True
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        if created and temporary.exists():
            temporary.unlink()
        raise


@contextmanager
def session_mutation_lock(workspace: Path, slot: str = DEFAULT_SLOT):
    """Acquire a non-blocking, slot-scoped local mutation lease.

    A contender fails closed instead of waiting behind an unknown process or
    deleting a possible crash marker. The caller must reload the verified
    frame and retry. Locks are runtime-only files and are removed only by the
    successful owner that created them.
    """

    normalized = validate_slot(slot)
    lock_path = workspace / LOCK_DIRECTORY / (normalized + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor: int | None = None
    try:
        descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError as error:
        raise SessionViolation("Session slot is busy; reload the verified frame and retry") from error
    try:
        os.write(descriptor, ("slot=" + normalized + "\n").encode("ascii"))
        os.fsync(descriptor)
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if lock_path.exists():
            lock_path.unlink()


def _load_legacy_bytes(path: Path) -> tuple[bytes, CreativeLedger]:
    if not path.is_file():
        raise SessionViolation("No legacy CreativeSession/v1 source exists")
    raw = path.read_bytes()
    try:
        record = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SessionViolation("Legacy session is not valid UTF-8 JSON") from error
    if not isinstance(record, Mapping) or record.get("schema") != LEGACY_SCHEMA:
        raise SessionViolation("Legacy session schema must be CreativeSession/v1")
    try:
        ledger = CreativeLedger.from_records(record.get("events", ()))
    except (LedgerViolation, KeyError, TypeError, ValueError) as error:
        raise SessionViolation("Legacy session ledger is invalid") from error
    return raw, ledger


@dataclass(frozen=True)
class MigrationResult:
    status: str
    legacy_path: str
    v2_path: str
    legacy_sha256: str
    timeline_hash: str
    event_count: int
    graph_revision: str
    slot_id: str = DEFAULT_SLOT

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "legacy_path": self.legacy_path,
            "v2_path": self.v2_path,
            "legacy_sha256": self.legacy_sha256,
            "timeline_hash": self.timeline_hash,
            "event_count": self.event_count,
            "graph_revision": self.graph_revision,
            "slot_id": self.slot_id,
        }


@dataclass(frozen=True)
class LoadedV2Session:
    ledger: CreativeLedger
    legacy_sha256: str
    timeline_hash: str
    graph_revision: str
    migrated_at: str
    slot_id: str = DEFAULT_SLOT


@dataclass(frozen=True)
class V2SourceVerification:
    """Evidence that a v2 envelope is still bound to its immutable v1 source.

    Loading a v2 envelope proves only that the envelope is internally
    self-consistent.  This separate result additionally proves that the source
    file which was present at migration time still exists, has the declared
    byte hash, and encodes the exact same event records.  It is deliberately
    read-only: a mismatch must never be "repaired" by replacing either file.
    """

    status: str
    legacy_path: str
    v2_path: str
    legacy_sha256: str
    timeline_hash: str
    graph_revision: str
    event_count: int
    state: StoryState
    slot_id: str = DEFAULT_SLOT

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "legacy_path": self.legacy_path,
            "v2_path": self.v2_path,
            "legacy_sha256": self.legacy_sha256,
            "timeline_hash": self.timeline_hash,
            "graph_revision": self.graph_revision,
            "event_count": self.event_count,
            "state": self.state.to_dict(),
            "slot_id": self.slot_id,
        }


@dataclass(frozen=True)
class VerifiedSessionReceipt:
    """Portable, no-event-content evidence for one source-verified v2 slot.

    The receipt transports identities and the public-safe final story state,
    never legacy bytes, event records, free text, vault references, or provider
    material. It can therefore support synthetic GitHub evidence and later
    local handoff coordination, but cannot restore or disclose a session.
    """

    receipt_id: str
    receipt_hash: str
    legacy_sha256: str
    timeline_hash: str
    graph_revision: str
    event_count: int
    state: StoryState
    slot_id: str = DEFAULT_SLOT

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "CreativeVerifiedSessionReceipt/v1",
            "status": "session_source_verified",
            "receipt_id": self.receipt_id,
            "receipt_hash": self.receipt_hash,
            "legacy_sha256": self.legacy_sha256,
            "timeline_hash": self.timeline_hash,
            "graph_revision": self.graph_revision,
            "event_count": self.event_count,
            "state": self.state.to_dict(),
            "slot_id": self.slot_id,
            "contains_event_records": False,
            "contains_customer_material": False,
            "external_provider_authorized": False,
            "authority_note": "Read-only provenance receipt; it cannot restore a session or authorize customer intake, deployment, or provider use.",
        }


def _build_v2_record(raw_legacy: bytes, ledger: CreativeLedger, migrated_at: str, slot: str) -> dict[str, Any]:
    try:
        verified = verified_director_input(ledger, graph_for_ledger(ledger))
    except (TimelineViolation, LedgerViolation, KeyError, TypeError, ValueError) as error:
        raise SessionViolation("Legacy session cannot be losslessly represented by the active story graph") from error
    return {
        "schema": SESSION_SCHEMA,
        "migration": {
            "legacy_schema": LEGACY_SCHEMA,
            "legacy_sha256": _sha256_bytes(raw_legacy),
            "legacy_event_count": len(ledger.events),
            "graph_revision": verified.graph_revision,
            "timeline_hash": verified.timeline_hash,
            "migrated_at": str(migrated_at),
            "slot_id": slot,
        },
        "events": ledger.to_records(),
    }


def _atomic_write_new(path: Path, content: str) -> None:
    """Create a new target atomically; never replace an existing save."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SessionViolation("Refusing to overwrite an existing v2 session")
    temporary = path.with_name(path.name + ".migration-tmp")
    if temporary.exists():
        raise SessionViolation("A prior incomplete migration temporary file exists")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise SessionViolation("Refusing to overwrite an existing v2 session")
        os.replace(temporary, path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def load_v2_session(workspace: Path, slot: str = DEFAULT_SLOT) -> LoadedV2Session:
    """Validate a v2 envelope against its graph-backed timeline declaration."""

    normalized_slot = validate_slot(slot)
    path = v2_session_path(workspace, normalized_slot)
    if not path.is_file():
        raise SessionViolation("No CreativeSession/v2 envelope exists")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SessionViolation("v2 session is not valid JSON") from error
    if not isinstance(record, Mapping) or record.get("schema") != SESSION_SCHEMA:
        raise SessionViolation("Unsupported v2 session schema")
    migration = record.get("migration")
    if not isinstance(migration, Mapping):
        raise SessionViolation("v2 session has no migration provenance")
    if migration.get("legacy_schema") != LEGACY_SCHEMA:
        raise SessionViolation("v2 session has an unsupported legacy schema")
    declared_slot = migration.get("slot_id", DEFAULT_SLOT)
    try:
        declared_slot = validate_slot(declared_slot)
    except SessionViolation as error:
        raise SessionViolation("v2 session slot is malformed") from error
    if declared_slot != normalized_slot:
        raise SessionViolation("v2 session slot does not match the requested slot")
    try:
        ledger = CreativeLedger.from_records(record.get("events", ()))
        verified = verified_director_input(ledger, graph_for_ledger(ledger))
    except (TimelineViolation, LedgerViolation, KeyError, TypeError, ValueError) as error:
        raise SessionViolation("v2 session ledger fails graph-backed replay") from error
    if migration.get("graph_revision") != verified.graph_revision:
        raise SessionViolation("v2 graph revision does not match the verified graph")
    if migration.get("timeline_hash") != verified.timeline_hash:
        raise SessionViolation("v2 timeline hash does not match the verified timeline")
    declared_event_count = migration.get("legacy_event_count")
    if isinstance(declared_event_count, bool) or not isinstance(declared_event_count, int):
        raise SessionViolation("v2 legacy event count is malformed")
    if declared_event_count != len(ledger.events):
        raise SessionViolation("v2 legacy event count does not match the ledger")
    legacy_hash = str(migration.get("legacy_sha256", ""))
    if len(legacy_hash) != 64:
        raise SessionViolation("v2 legacy SHA-256 is malformed")
    return LoadedV2Session(
        ledger=ledger,
        legacy_sha256=legacy_hash,
        timeline_hash=verified.timeline_hash,
        graph_revision=verified.graph_revision,
        migrated_at=str(migration.get("migrated_at", "")),
        slot_id=normalized_slot,
    )


def verify_v2_source_binding(workspace: Path, slot: str = DEFAULT_SLOT) -> V2SourceVerification:
    """Fail closed unless the v2 save still exactly represents its v1 source.

    The byte hash is the immutable-source identity, while exact event-record
    equality makes the intended relationship easy to inspect and protects the
    invariant even if this code is later refactored.  The separate replays
    retain the graph/timeline guarantees on both sides of the binding.
    """

    normalized_slot = validate_slot(slot)
    loaded = load_v2_session(workspace, normalized_slot)
    legacy_path = legacy_session_path(workspace, normalized_slot)
    raw_legacy, legacy_ledger = _load_legacy_bytes(legacy_path)
    source_hash = _sha256_bytes(raw_legacy)
    if source_hash != loaded.legacy_sha256:
        raise SessionViolation("v2 session no longer matches immutable legacy source bytes")
    try:
        legacy_verified = verified_director_input(legacy_ledger, graph_for_ledger(legacy_ledger))
        v2_verified = verified_director_input(loaded.ledger, graph_for_ledger(loaded.ledger))
    except (TimelineViolation, LedgerViolation, KeyError, TypeError, ValueError) as error:
        raise SessionViolation("v2 or legacy session fails graph-backed source verification") from error
    if legacy_ledger.to_records() != loaded.ledger.to_records():
        raise SessionViolation("v2 event records differ from immutable legacy source")
    if legacy_verified.timeline_hash != loaded.timeline_hash or v2_verified.timeline_hash != loaded.timeline_hash:
        raise SessionViolation("v2 and legacy timeline identities do not agree")
    if legacy_verified.graph_revision != loaded.graph_revision or v2_verified.graph_revision != loaded.graph_revision:
        raise SessionViolation("v2 and legacy graph revisions do not agree")
    return V2SourceVerification(
        status="v2_source_verified",
        legacy_path=str(legacy_path),
        v2_path=str(v2_session_path(workspace, normalized_slot)),
        legacy_sha256=source_hash,
        timeline_hash=loaded.timeline_hash,
        graph_revision=loaded.graph_revision,
        event_count=len(loaded.ledger.events),
        state=v2_verified.state,
        slot_id=normalized_slot,
    )


def build_verified_session_receipt(workspace: Path, slot: str = DEFAULT_SLOT) -> VerifiedSessionReceipt:
    """Create deterministic content-minimal handoff evidence for a v2 slot."""

    verified = verify_v2_source_binding(workspace, slot)
    material = {
        "schema": "CreativeVerifiedSessionReceipt/v1",
        "legacy_sha256": verified.legacy_sha256,
        "timeline_hash": verified.timeline_hash,
        "graph_revision": verified.graph_revision,
        "event_count": verified.event_count,
        "state": verified.state.to_dict(),
        "slot_id": verified.slot_id,
    }
    receipt_hash = _sha256_bytes(canonical_json(material).encode("utf-8"))
    return VerifiedSessionReceipt(
        receipt_id="session_receipt_" + receipt_hash[:20],
        receipt_hash=receipt_hash,
        legacy_sha256=verified.legacy_sha256,
        timeline_hash=verified.timeline_hash,
        graph_revision=verified.graph_revision,
        event_count=verified.event_count,
        state=verified.state,
        slot_id=verified.slot_id,
    )


def migrate_legacy_session(workspace: Path, migrated_at: str, slot: str = DEFAULT_SLOT) -> MigrationResult:
    """Create an idempotent v2 envelope only when legacy replay is lossless."""

    normalized_slot = validate_slot(slot)
    legacy_path = legacy_session_path(workspace, normalized_slot)
    before, ledger = _load_legacy_bytes(legacy_path)
    record = _build_v2_record(before, ledger, migrated_at, normalized_slot)
    target = v2_session_path(workspace, normalized_slot)
    legacy_hash = _sha256_bytes(before)
    if target.exists():
        loaded = load_v2_session(workspace, normalized_slot)
        if loaded.legacy_sha256 != legacy_hash:
            raise SessionViolation("Existing v2 session refers to a different legacy source")
        if loaded.timeline_hash != record["migration"]["timeline_hash"]:
            raise SessionViolation("Existing v2 session timeline differs from the current verified source")
        if legacy_path.read_bytes() != before:
            raise SessionViolation("Legacy source changed during migration check")
        return MigrationResult(
            "already_migrated",
            str(legacy_path),
            str(target),
            legacy_hash,
            loaded.timeline_hash,
            len(ledger.events),
            loaded.graph_revision,
            normalized_slot,
        )
    content = canonical_json(record) + "\n"
    _atomic_write_new(target, content)
    if legacy_path.read_bytes() != before:
        raise SessionViolation("Legacy source changed during migration")
    loaded = load_v2_session(workspace, normalized_slot)
    return MigrationResult(
        "migrated",
        str(legacy_path),
        str(target),
        legacy_hash,
        loaded.timeline_hash,
        len(ledger.events),
        loaded.graph_revision,
        normalized_slot,
    )
