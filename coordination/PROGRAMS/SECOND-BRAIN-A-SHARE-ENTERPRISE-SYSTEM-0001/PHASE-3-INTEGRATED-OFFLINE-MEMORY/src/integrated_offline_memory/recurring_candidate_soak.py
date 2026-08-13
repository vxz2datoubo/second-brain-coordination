"""One-shot, scheduler-safe candidate-only recurring ingestion runtime.

This module deliberately owns no memory/query authority.  It places a stable
snapshot and a single-writer guard around the established Daily-v2 bridge and
``MemoryStore``.  Its receipt ledger contains only the bridge's public-safe
aggregate receipt fields.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

from .memory_store import MemoryStore
from .private_candidate_ingestion import (
    ingest_daily_memory_candidate_v2,
    serialize_daily_memory_candidate_v2_report,
    validate_private_data_paths,
)


OPERATIONAL_STORE_LEAF = "cltm-private-candidate-runtime.sqlite3"
FROZEN_CANARY_STORE_LEAF = "cltm-private-canary-r98.sqlite3"
LOCK_LEAF = ".cltm-private-candidate-runtime.lock"
LEDGER_LEAF = "cltm-private-candidate-runtime-soak-ledger.jsonl"

_RECEIPT_FIELDS = frozenset({
    "schema_version", "status", "validation_status", "candidate_authority_only",
    "formal_project_global_write", "source_hash", "pointer_hash", "episode_id_hash",
    "atom_id_hash", "scope_hash", "candidate_count", "imported_count", "duplicate_count",
    "non_imported_count", "recall_count", "exact_imported_atom_recalled", "recorded_at_hash",
})


class RecurringCandidateSoakError(ValueError):
    """A redacted, scheduler-safe operational failure."""


@dataclass(frozen=True)
class StableSourceSnapshot:
    package: dict[str, Any]


def _stat_signature(path: Path) -> tuple[int, int, int, int]:
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def load_stable_daily_v2_snapshot(source: Path, private_root: Path) -> StableSourceSnapshot:
    """Read one exact bound package only when its metadata remains unchanged."""

    source, _, _ = validate_private_data_paths(source, source.with_suffix(".probe"), private_root)
    try:
        before = _stat_signature(source)
        raw = source.read_bytes()
        after = _stat_signature(source)
    except OSError as error:
        raise RecurringCandidateSoakError("SOURCE_UNAVAILABLE") from error
    if before != after:
        raise RecurringCandidateSoakError("SOURCE_UNSTABLE")
    try:
        package = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RecurringCandidateSoakError("SOURCE_INVALID") from error
    if not isinstance(package, dict):
        raise RecurringCandidateSoakError("SOURCE_MAPPING_REQUIRED")
    # Validate before opening the durable store, while ingestion validates again.
    try:
        serialize_daily_memory_candidate_v2_report(package)
    except ValueError as error:
        raise RecurringCandidateSoakError("SOURCE_VALIDATION_FAILED") from error
    return StableSourceSnapshot(package)


@contextmanager
def _single_writer_lock(private_root: Path) -> Iterator[None]:
    lock = private_root / LOCK_LEAF
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise RecurringCandidateSoakError("CONCURRENT_RUN_REJECTED") from error
    except OSError as error:
        raise RecurringCandidateSoakError("CONCURRENCY_GUARD_FAILED") from error
    try:
        os.close(descriptor)
        yield
    finally:
        try:
            lock.unlink(missing_ok=True)
        except OSError as error:
            raise RecurringCandidateSoakError("CONCURRENCY_GUARD_CLEANUP_FAILED") from error


def _safe_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    public = {key: receipt[key] for key in _RECEIPT_FIELDS if key in receipt}
    public["status"] = "NO_CHANGE" if public.get("status") == "IDEMPOTENT_DUPLICATE" else public.get("status")
    public["candidate_authority_only"] = True
    public["formal_project_global_write"] = "LOCKED"
    return public


def _append_ledger(private_root: Path, receipt: Mapping[str, Any]) -> None:
    ledger = private_root / LEDGER_LEAF
    try:
        with ledger.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(_safe_receipt(receipt), ensure_ascii=True, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as error:
        raise RecurringCandidateSoakError("SOAK_LEDGER_WRITE_FAILED") from error


def run_recurring_candidate_ingestion(
    source_path: Path, private_root: Path, *, store_path: Path | None = None,
) -> dict[str, Any]:
    """Execute one candidate-only recurring run against one durable store."""

    store_path = store_path or private_root / OPERATIONAL_STORE_LEAF
    source, store, root = validate_private_data_paths(source_path, store_path, private_root)
    if store.name == FROZEN_CANARY_STORE_LEAF:
        raise RecurringCandidateSoakError("FROZEN_CANARY_STORE_DENIED")
    if store.name != OPERATIONAL_STORE_LEAF:
        raise RecurringCandidateSoakError("OPERATIONAL_STORE_NAME_REQUIRED")
    snapshot = load_stable_daily_v2_snapshot(source, root)
    with _single_writer_lock(root):
        memory = MemoryStore(store).connect()
        try:
            try:
                result = ingest_daily_memory_candidate_v2(snapshot.package, memory)
            except ValueError as error:
                raise RecurringCandidateSoakError("INGESTION_REJECTED") from error
            receipt = _safe_receipt(result.public_receipt())
            _append_ledger(root, receipt)
            return receipt
        finally:
            memory.close()


def run_from_environment(environment: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Scheduler-safe one-shot entry point; bindings must already be explicit."""

    env = os.environ if environment is None else environment
    root, source = env.get("CLTM_PRIVATE_DATA_ROOT"), env.get("CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH")
    if not root or not source:
        raise RecurringCandidateSoakError("PRIVATE_BINDING_REQUIRED")
    return run_recurring_candidate_ingestion(Path(source), Path(root))
