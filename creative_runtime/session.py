"""Durable, fail-closed session envelopes for the offline creative runtime.

`CreativeSession/v1` remains the legacy source file.  `CreativeSession/v2`
wraps an identical ledger with an explicit graph/timeline provenance record.
Migration never edits or renames the legacy source; it produces a separate,
atomically written envelope only after semantic replay succeeds.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .continuity import TimelineViolation, graph_for_ledger, verified_director_input
from .contracts import canonical_json
from .ledger import CreativeLedger, LedgerViolation


LEGACY_SCHEMA = "CreativeSession/v1"
SESSION_SCHEMA = "CreativeSession/v2"
LEGACY_FILENAME = "session.json"
V2_DIRECTORY = "saves"
V2_FILENAME = "default.json"


class SessionViolation(ValueError):
    """Raised when a session cannot be migrated or its provenance is invalid."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def legacy_session_path(workspace: Path) -> Path:
    return workspace / LEGACY_FILENAME


def v2_session_path(workspace: Path) -> Path:
    return workspace / V2_DIRECTORY / V2_FILENAME


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "legacy_path": self.legacy_path,
            "v2_path": self.v2_path,
            "legacy_sha256": self.legacy_sha256,
            "timeline_hash": self.timeline_hash,
            "event_count": self.event_count,
            "graph_revision": self.graph_revision,
        }


@dataclass(frozen=True)
class LoadedV2Session:
    ledger: CreativeLedger
    legacy_sha256: str
    timeline_hash: str
    graph_revision: str
    migrated_at: str


def _build_v2_record(raw_legacy: bytes, ledger: CreativeLedger, migrated_at: str) -> dict[str, Any]:
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


def load_v2_session(workspace: Path) -> LoadedV2Session:
    """Validate a v2 envelope against its graph-backed timeline declaration."""

    path = v2_session_path(workspace)
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
    try:
        ledger = CreativeLedger.from_records(record.get("events", ()))
        verified = verified_director_input(ledger, graph_for_ledger(ledger))
    except (TimelineViolation, LedgerViolation, KeyError, TypeError, ValueError) as error:
        raise SessionViolation("v2 session ledger fails graph-backed replay") from error
    if migration.get("graph_revision") != verified.graph_revision:
        raise SessionViolation("v2 graph revision does not match the verified graph")
    if migration.get("timeline_hash") != verified.timeline_hash:
        raise SessionViolation("v2 timeline hash does not match the verified timeline")
    if int(migration.get("legacy_event_count", -1)) != len(ledger.events):
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
    )


def migrate_legacy_session(workspace: Path, migrated_at: str) -> MigrationResult:
    """Create an idempotent v2 envelope only when legacy replay is lossless."""

    legacy_path = legacy_session_path(workspace)
    before, ledger = _load_legacy_bytes(legacy_path)
    record = _build_v2_record(before, ledger, migrated_at)
    target = v2_session_path(workspace)
    legacy_hash = _sha256_bytes(before)
    if target.exists():
        loaded = load_v2_session(workspace)
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
        )
    content = canonical_json(record) + "\n"
    _atomic_write_new(target, content)
    if legacy_path.read_bytes() != before:
        raise SessionViolation("Legacy source changed during migration")
    loaded = load_v2_session(workspace)
    return MigrationResult(
        "migrated",
        str(legacy_path),
        str(target),
        legacy_hash,
        loaded.timeline_hash,
        len(ledger.events),
        loaded.graph_revision,
    )
