"""Public-safe fixed runner template for CLTM-0021 epoch 91 private-store writability diagnostics.

This file contains no private path or candidate content. It is a source template only. The executable
runner must be materialized under the OS temporary directory and compiled there before any private-root access.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


SCHEMA_VERSION = "103.3"
PLAIN_MARKER = b"CLTM_R91_WRITE_PROBE"
R90_LEAF = "cltm-private-canary-r90.sqlite3"
PLAIN_LEAF = ".cltm-private-write-probe-r91.tmp"
SQLITE_LEAF = "cltm-private-memorystore-probe-r91.sqlite3"


def emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True))


def leaf_state(path: Path) -> str:
    if not path.exists():
        return "NONE"
    if path.is_file():
        return "FILE"
    if path.is_dir():
        return "DIRECTORY"
    return "OTHER"


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def remove_owned_sqlite_artifacts(database: Path) -> bool:
    ok = True
    for item in (database, Path(str(database) + "-wal"), Path(str(database) + "-shm")):
        try:
            if item.exists():
                item.unlink()
        except OSError:
            ok = False
    return ok


def base_receipt() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PRIVATE_ROOT_BINDING_OR_SHAPE_INVALID",
        "root_binding_present": False,
        "root_shape_valid": False,
        "r90_store_leaf_state": "NONE",
        "plain_write_probe": "NOT_RUN",
        "sqlite_memorystore_probe": "NOT_RUN",
        "cleanup_status": "NOT_REQUIRED",
        "LOCAL_EXECUTION_ISSUES": [],
        "lock_statement": "NO_PRIVATE_CANDIDATE_ACCESS_OR_INGESTION_RECALL_CANARY",
    }


def main() -> None:
    receipt = base_receipt()
    raw_root = os.environ.get("CLTM_PRIVATE_DATA_ROOT")
    raw_public_root = os.environ.get("CLTM_PUBLIC_REPO_ROOT")
    receipt["root_binding_present"] = bool(raw_root)
    if not raw_root or not raw_public_root:
        receipt["LOCAL_EXECUTION_ISSUES"] = ["PRIVATE_OR_PUBLIC_ROOT_BINDING_MISSING"]
        emit(receipt)
        return

    try:
        root = Path(raw_root).resolve(strict=True)
        public_root = Path(raw_public_root).resolve(strict=True)
    except OSError:
        receipt["LOCAL_EXECUTION_ISSUES"] = ["PRIVATE_OR_PUBLIC_ROOT_RESOLUTION_FAILED"]
        emit(receipt)
        return

    if not root.is_dir() or is_within(root, public_root) or is_within(public_root, root):
        receipt["LOCAL_EXECUTION_ISSUES"] = ["PRIVATE_ROOT_SHAPE_OR_BOUNDARY_INVALID"]
        emit(receipt)
        return

    receipt["root_shape_valid"] = True
    receipt["r90_store_leaf_state"] = leaf_state(root / R90_LEAF)

    plain = root / PLAIN_LEAF
    if plain.exists():
        receipt["status"] = "PRIVATE_STORE_DIAGNOSTIC_PROBE_NOT_FRESH"
        receipt["plain_write_probe"] = "NOT_FRESH"
        receipt["LOCAL_EXECUTION_ISSUES"] = ["PLAIN_PROBE_PREEXISTING"]
        emit(receipt)
        return

    plain_fd: int | None = None
    plain_owned = False
    try:
        plain_fd = os.open(plain, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        plain_owned = True
    except FileExistsError:
        receipt["status"] = "PRIVATE_STORE_DIAGNOSTIC_PROBE_NOT_FRESH"
        receipt["plain_write_probe"] = "NOT_FRESH"
        receipt["LOCAL_EXECUTION_ISSUES"] = ["PLAIN_PROBE_RACE_PREEXISTING"]
        emit(receipt)
        return
    except OSError:
        receipt["status"] = "PRIVATE_ROOT_PLAIN_WRITE_PROBE_FAILED"
        receipt["plain_write_probe"] = "FAILED"
        receipt["cleanup_status"] = "NOT_REQUIRED"
        receipt["LOCAL_EXECUTION_ISSUES"] = ["PLAIN_CREATE_OSERROR_REDACTED"]
        emit(receipt)
        return

    try:
        written = os.write(plain_fd, PLAIN_MARKER)
        if written != len(PLAIN_MARKER):
            raise OSError("short_write")
        os.fsync(plain_fd)
        os.close(plain_fd)
        plain_fd = None
    except OSError:
        if plain_fd is not None:
            try:
                os.close(plain_fd)
            except OSError:
                pass
        cleanup_ok = True
        if plain_owned:
            try:
                if plain.exists():
                    plain.unlink()
            except OSError:
                cleanup_ok = False
        receipt["plain_write_probe"] = "FAILED"
        receipt["cleanup_status"] = "PASS" if cleanup_ok else "CLEANUP_FAILED"
        receipt["status"] = (
            "PRIVATE_ROOT_PLAIN_WRITE_PROBE_FAILED"
            if cleanup_ok
            else "PRIVATE_STORE_DIAGNOSTIC_CLEANUP_FAILED"
        )
        receipt["LOCAL_EXECUTION_ISSUES"] = ["PLAIN_WRITE_OSERROR_REDACTED"]
        emit(receipt)
        return

    try:
        plain.unlink()
    except OSError:
        receipt["plain_write_probe"] = "PASS"
        receipt["cleanup_status"] = "CLEANUP_FAILED"
        receipt["status"] = "PRIVATE_STORE_DIAGNOSTIC_CLEANUP_FAILED"
        receipt["LOCAL_EXECUTION_ISSUES"] = ["PLAIN_PROBE_DELETE_FAILED"]
        emit(receipt)
        return

    receipt["plain_write_probe"] = "PASS"

    database = root / SQLITE_LEAF
    wal = Path(str(database) + "-wal")
    shm = Path(str(database) + "-shm")
    if database.exists() or wal.exists() or shm.exists():
        receipt["status"] = "PRIVATE_STORE_DIAGNOSTIC_PROBE_NOT_FRESH"
        receipt["sqlite_memorystore_probe"] = "NOT_FRESH"
        receipt["LOCAL_EXECUTION_ISSUES"] = ["SQLITE_PROBE_PREEXISTING"]
        emit(receipt)
        return

    reserve_fd: int | None = None
    try:
        reserve_fd = os.open(database, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(reserve_fd)
        reserve_fd = None
    except FileExistsError:
        receipt["status"] = "PRIVATE_STORE_DIAGNOSTIC_PROBE_NOT_FRESH"
        receipt["sqlite_memorystore_probe"] = "NOT_FRESH"
        receipt["LOCAL_EXECUTION_ISSUES"] = ["SQLITE_PROBE_RACE_PREEXISTING"]
        emit(receipt)
        return
    except OSError:
        if reserve_fd is not None:
            try:
                os.close(reserve_fd)
            except OSError:
                pass
        receipt["status"] = "PRIVATE_ROOT_MEMORYSTORE_SQLITE_PROBE_FAILED"
        receipt["sqlite_memorystore_probe"] = "FAILED"
        receipt["cleanup_status"] = "NOT_REQUIRED"
        receipt["LOCAL_EXECUTION_ISSUES"] = ["SQLITE_RESERVATION_OSERROR_REDACTED"]
        emit(receipt)
        return

    store = None
    try:
        from integrated_offline_memory.memory_store import MemoryStore

        store = MemoryStore(database).connect()
        store.close()
        store = None
    except Exception:
        if store is not None:
            try:
                store.close()
            except Exception:
                pass
        cleanup_ok = remove_owned_sqlite_artifacts(database)
        receipt["sqlite_memorystore_probe"] = "FAILED"
        receipt["cleanup_status"] = "PASS" if cleanup_ok else "CLEANUP_FAILED"
        receipt["status"] = (
            "PRIVATE_ROOT_MEMORYSTORE_SQLITE_PROBE_FAILED"
            if cleanup_ok
            else "PRIVATE_STORE_DIAGNOSTIC_CLEANUP_FAILED"
        )
        receipt["LOCAL_EXECUTION_ISSUES"] = ["MEMORYSTORE_SQLITE_EXCEPTION_REDACTED"]
        emit(receipt)
        return

    cleanup_ok = remove_owned_sqlite_artifacts(database)
    receipt["sqlite_memorystore_probe"] = "PASS"
    receipt["cleanup_status"] = "PASS" if cleanup_ok else "CLEANUP_FAILED"
    receipt["status"] = (
        "PRIVATE_STORE_WRITEABILITY_DIAGNOSTIC_PASS"
        if cleanup_ok
        else "PRIVATE_STORE_DIAGNOSTIC_CLEANUP_FAILED"
    )
    if not cleanup_ok:
        receipt["LOCAL_EXECUTION_ISSUES"] = ["SQLITE_PROBE_DELETE_FAILED"]
    emit(receipt)


if __name__ == "__main__":
    main()
