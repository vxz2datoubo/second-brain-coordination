"""Versioned, root-confined save slots for deterministic creative sessions."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping

from .contracts import canonical_json
from .ledger import CreativeLedger, LedgerViolation


CURRENT_SESSION_SCHEMA = "CreativeSession/v2"
_SLOT = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
_RESERVED = {"con", "prn", "aux", "nul", *(f"com{number}" for number in range(1, 10)), *(f"lpt{number}" for number in range(1, 10))}


class SaveSlotViolation(ValueError):
    """Raised for unsafe paths, malformed sessions, or unsupported migration."""


@dataclass(frozen=True)
class LoadedSession:
    ledger: CreativeLedger
    manifest_hash: str
    schema: str
    migrations: tuple[str, ...] = ()


def migrate_session(record: Mapping[str, Any], expected_manifest_hash: str) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Perform explicit version migration without altering ledger event records."""

    schema = record.get("schema")
    if schema == CURRENT_SESSION_SCHEMA:
        migrated = dict(record)
        if migrated.get("manifest_hash") != expected_manifest_hash:
            raise SaveSlotViolation("Save manifest hash does not match the current graph")
        return migrated, ()
    if schema == "CreativeSession/v1":
        events = record.get("events")
        if not isinstance(events, list):
            raise SaveSlotViolation("Legacy session has no event list")
        return {
            "schema": CURRENT_SESSION_SCHEMA,
            "manifest_hash": expected_manifest_hash,
            "events": events,
            "migration_history": ["CreativeSession/v1->v2"],
        }, ("CreativeSession/v1->v2",)
    raise SaveSlotViolation("Unsupported session schema: " + str(schema))


class SaveStore:
    """Filesystem helper that confines every save operation to one configured root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _name(self, slot: str) -> str:
        normalized = str(slot).casefold()
        if not _SLOT.fullmatch(normalized) or normalized in _RESERVED:
            raise SaveSlotViolation("Invalid save slot name")
        return normalized

    def _path(self, slot: str) -> Path:
        name = self._name(slot)
        candidate = (self.root / f"{name}.json").resolve()
        if candidate.parent != self.root:
            raise SaveSlotViolation("Save slot escapes configured root")
        return candidate

    def list_slots(self) -> list[str]:
        if not self.root.exists():
            return []
        if not self.root.is_dir():
            raise SaveSlotViolation("Save root is not a directory")
        return sorted(path.stem for path in self.root.glob("*.json") if path.is_file() and _SLOT.fullmatch(path.stem))

    def save(self, slot: str, ledger: CreativeLedger, manifest_hash: str) -> Path:
        target = self._path(slot)
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": CURRENT_SESSION_SCHEMA,
            "manifest_hash": manifest_hash,
            "events": ledger.to_records(),
            "migration_history": [],
        }
        descriptor, temporary_name = tempfile.mkstemp(prefix=".save-", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(canonical_json(payload) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, target)
        except OSError as error:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            finally:
                raise SaveSlotViolation("Save replacement failed") from error
        return target

    def load(self, slot: str, expected_manifest_hash: str) -> LoadedSession:
        path = self._path(slot)
        if not path.is_file():
            raise SaveSlotViolation("Save slot does not exist")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, Mapping):
                raise SaveSlotViolation("Save payload must be an object")
            record, migrations = migrate_session(raw, expected_manifest_hash)
            ledger = CreativeLedger.from_records(record["events"])
        except (json.JSONDecodeError, KeyError, LedgerViolation, TypeError) as error:
            raise SaveSlotViolation("Save slot is corrupt or incompatible") from error
        return LoadedSession(ledger=ledger, manifest_hash=expected_manifest_hash, schema=CURRENT_SESSION_SCHEMA, migrations=migrations)

    def delete(self, slot: str) -> bool:
        path = self._path(slot)
        if not path.exists():
            return False
        if not path.is_file():
            raise SaveSlotViolation("Save slot path is not a file")
        path.unlink()
        return True
