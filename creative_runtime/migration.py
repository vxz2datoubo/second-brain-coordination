"""Fail-closed, lossless migration of the original creative session ledger.

The migration deliberately does not reinterpret legacy actions through a newer
story graph.  A verified v1 ledger is embedded unchanged in the v2 envelope,
with its replayed state and source digest.  Publication is create-only: output
is staged, the legacy source is re-read and re-fingerprinted, and only then is
the staged file linked into its final name.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping

from .contracts import canonical_json
from .ledger import CreativeLedger, LedgerViolation


LEGACY_SCHEMA = "CreativeSession/v1"
CURRENT_SCHEMA = "CreativeSession/v2"
_SAFE_SLOT = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


class MigrationViolation(ValueError):
    """Raised when migration cannot prove a lossless, race-safe result."""


def _source_fingerprint(path: Path) -> tuple[int, int, int, int, int]:
    stat_result = path.stat()
    return (
        int(stat_result.st_dev),
        int(stat_result.st_ino),
        int(stat_result.st_size),
        int(stat_result.st_mtime_ns),
        int(stat_result.st_ctime_ns),
    )


def _read_regular_source(path: Path) -> tuple[bytes, tuple[int, int, int, int, int]]:
    if path.is_symlink() or not path.is_file():
        raise MigrationViolation("Legacy session must be a regular, non-symlink file")
    before = _source_fingerprint(path)
    data = path.read_bytes()
    after = _source_fingerprint(path)
    if before != after or len(data) != before[2]:
        raise MigrationViolation("Legacy session changed while it was being read")
    return data, after


def _decode_legacy(source_bytes: bytes) -> tuple[dict[str, Any], CreativeLedger]:
    try:
        text = source_bytes.decode("utf-8", errors="strict")
        document = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MigrationViolation("Legacy session is not strict UTF-8 JSON") from error
    if not isinstance(document, dict) or document.get("schema") != LEGACY_SCHEMA:
        raise MigrationViolation("Unsupported legacy session schema")
    records = document.get("events")
    if not isinstance(records, list) or not records:
        raise MigrationViolation("Legacy session requires a non-empty event ledger")
    try:
        ledger = CreativeLedger.from_records(records)
        ledger.replay()
    except (KeyError, TypeError, ValueError, LedgerViolation) as error:
        raise MigrationViolation("Legacy event ledger is not replayable") from error
    return document, ledger


def _build_v2_document(source_bytes: bytes, ledger: CreativeLedger) -> dict[str, Any]:
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    return {
        "schema": CURRENT_SCHEMA,
        "migration": {
            "kind": "lossless_legacy_envelope",
            "source_schema": LEGACY_SCHEMA,
            "source_sha256": source_sha256,
            "legacy_event_count": len(ledger.events),
        },
        "events": ledger.to_records(),
        "replayed_state": ledger.replay().to_dict(),
    }


def _write_staged(directory: Path, payload: bytes) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, raw_path = tempfile.mkstemp(prefix=".session-v2-", suffix=".tmp", dir=directory)
    staged = Path(raw_path)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        return staged
    except BaseException:
        staged.unlink(missing_ok=True)
        raise


def _publish_create_only(staged: Path, target: Path) -> None:
    """Atomically create *target* without ever replacing an existing file."""

    try:
        os.link(staged, target)
    except FileExistsError as error:
        raise MigrationViolation("A v2 session already exists at the target slot") from error
    finally:
        staged.unlink(missing_ok=True)


def _validated_existing_target(target: Path, expected_source_hash: str) -> bool:
    if target.is_symlink():
        raise MigrationViolation("Existing v2 target must not be a symlink")
    if not target.exists():
        return False
    if not target.is_file():
        raise MigrationViolation("Existing v2 target is not a regular file")
    try:
        document = json.loads(target.read_text(encoding="utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MigrationViolation("Existing v2 target is invalid") from error
    migration = document.get("migration") if isinstance(document, Mapping) else None
    if (
        document.get("schema") != CURRENT_SCHEMA
        or not isinstance(migration, Mapping)
        or migration.get("source_sha256") != expected_source_hash
    ):
        raise MigrationViolation("Existing v2 target does not match this legacy source")
    try:
        CreativeLedger.from_records(document.get("events", [])).replay()
    except (KeyError, TypeError, ValueError, LedgerViolation) as error:
        raise MigrationViolation("Existing v2 target ledger is invalid") from error
    return True


def _ensure_save_directory(workspace: Path) -> Path:
    save_directory = workspace / "saves"
    if save_directory.is_symlink():
        raise MigrationViolation("Save directory must not be a symlink")
    save_directory.mkdir(parents=True, exist_ok=True)
    if save_directory.is_symlink() or not save_directory.is_dir():
        raise MigrationViolation("Save directory must be a regular directory")
    return save_directory


def migrate_legacy_session(workspace: Path, slot: str = "default") -> Path:
    """Migrate ``workspace/session.json`` to ``workspace/saves/<slot>.json``.

    On every failure the legacy bytes remain untouched.  A race detected after
    staging leaves no newly published v2 file.  A target that existed before
    the call is never removed or replaced.
    """

    if not _SAFE_SLOT.fullmatch(slot):
        raise MigrationViolation("Unsafe save slot")
    workspace = Path(workspace)
    source = workspace / "session.json"
    target = _ensure_save_directory(workspace) / f"{slot}.json"
    source_bytes, source_fingerprint = _read_regular_source(source)
    _document, ledger = _decode_legacy(source_bytes)
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if _validated_existing_target(target, source_hash):
        return target

    payload = (canonical_json(_build_v2_document(source_bytes, ledger)) + "\n").encode("utf-8")
    staged = _write_staged(target.parent, payload)
    try:
        final_bytes, final_fingerprint = _read_regular_source(source)
        if final_bytes != source_bytes or final_fingerprint != source_fingerprint:
            raise MigrationViolation("Legacy session changed before v2 publication")
        _publish_create_only(staged, target)
    except BaseException:
        staged.unlink(missing_ok=True)
        raise
    return target
