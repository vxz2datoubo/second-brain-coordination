"""Epoch 98 local/private canary runner.

Public-safe source template. It reads the explicitly bound DailyMemoryCandidate-v2
package only at execution time on the owner's machine, ingests exactly one eligible
user candidate into a fresh isolated private SQLite store, and emits aggregate/hash
receipt data only. It never prints private paths or semantic candidate content.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from integrated_offline_memory.memory_store import MemoryStore
from integrated_offline_memory.private_candidate_ingestion import (
    daily_memory_candidate_transport_to_w3_private_envelopes,
    ingest_daily_memory_candidate_v2,
    load_daily_memory_candidate_v2,
    serialize_daily_memory_candidate_v2_report,
    validate_private_data_paths,
)

ROOT_ENV = "CLTM_PRIVATE_DATA_ROOT"
SOURCE_ENV = "CLTM_PRIVATE_DAILY_MEMORY_CANDIDATE_V2_PATH"
STORE_LEAF = "cltm-private-canary-r98.sqlite3"


def _base_receipt() -> dict[str, Any]:
    return {
        "schema_version": "105.0",
        "status": "PRIVATE_CANARY_FAILED",
        "root_binding_present": False,
        "source_binding_present": False,
        "root_shape_valid": False,
        "source_shape_valid": False,
        "candidate_count_preflight": 0,
        "eligible_candidate_count": 0,
        "store_fresh": False,
        "ingestion_status": "NOT_RUN",
        "validation_status": "NOT_RUN",
        "candidate_authority_only": True,
        "formal_project_global_write": "LOCKED",
        "imported_count": 0,
        "duplicate_count": 0,
        "non_imported_count": 0,
        "recall_count": 0,
        "exact_imported_atom_recalled": False,
        "source_hash": None,
        "pointer_hash": None,
        "episode_id_hash": None,
        "atom_id_hash": None,
        "scope_hash": None,
        "recorded_at_hash": None,
        "LOCAL_EXECUTION_ISSUES": [],
        "lock_statement": "REAL_PRIVATE_CANARY_CANDIDATE_ONLY_FORMAL_PROJECT_GLOBAL_LOCKED",
    }


def _emit(receipt: dict[str, Any]) -> None:
    print(json.dumps(receipt, ensure_ascii=True, separators=(",", ":"), sort_keys=True))


def main() -> int:
    out = _base_receipt()
    root_raw = os.environ.get(ROOT_ENV)
    source_raw = os.environ.get(SOURCE_ENV)
    out["root_binding_present"] = bool(root_raw and root_raw.strip())
    out["source_binding_present"] = bool(source_raw and source_raw.strip())
    if not out["root_binding_present"] or not out["source_binding_present"]:
        out["status"] = "PRIVATE_SOURCE_BINDING_WAITING"
        _emit(out)
        return 0

    root = Path(root_raw)
    source = Path(source_raw)
    store_path = root / STORE_LEAF

    try:
        source_resolved, store_resolved, root_resolved = validate_private_data_paths(source, store_path, root)
        wal_path = Path(str(store_resolved) + "-wal")
        shm_path = Path(str(store_resolved) + "-shm")
        out["root_shape_valid"] = root_resolved.exists() and root_resolved.is_dir()
        out["source_shape_valid"] = source_resolved.is_file()
        if not out["root_shape_valid"] or not out["source_shape_valid"]:
            out["status"] = "PRIVATE_SOURCE_BINDING_OR_SHAPE_INVALID"
            _emit(out)
            return 0

        package = load_daily_memory_candidate_v2(source_resolved, root_resolved)
        raw_candidates = package.get("MEMORY_CANDIDATES", [])
        out["candidate_count_preflight"] = len(raw_candidates) if isinstance(raw_candidates, list) else -1
        transport = serialize_daily_memory_candidate_v2_report(package)
        envelopes, no_ops = daily_memory_candidate_transport_to_w3_private_envelopes(transport)
        out["eligible_candidate_count"] = len(envelopes)
        if out["candidate_count_preflight"] != 1 or len(envelopes) != 1 or len(no_ops) != 0:
            out["status"] = "PRIVATE_CANARY_EXACT_ONE_ELIGIBLE_CANDIDATE_REQUIRED"
            _emit(out)
            return 0

        if store_resolved.exists() or wal_path.exists() or shm_path.exists():
            out["status"] = "PRIVATE_CANARY_STORE_LEAF_NOT_FRESH"
            _emit(out)
            return 0
        out["store_fresh"] = True

        store = MemoryStore(store_resolved)
        try:
            store.connect()
            result = ingest_daily_memory_candidate_v2(package, store)
            public = result.public_receipt()
        finally:
            store.close()

        out["ingestion_status"] = public.get("status", "UNKNOWN")
        for key in (
            "validation_status",
            "candidate_authority_only",
            "formal_project_global_write",
            "source_hash",
            "pointer_hash",
            "episode_id_hash",
            "atom_id_hash",
            "scope_hash",
            "recorded_at_hash",
            "imported_count",
            "duplicate_count",
            "non_imported_count",
            "recall_count",
            "exact_imported_atom_recalled",
        ):
            out[key] = public.get(key)

        if (
            public.get("status") == "IMPORTED"
            and public.get("validation_status") == "PASS"
            and public.get("candidate_authority_only") is True
            and public.get("formal_project_global_write") == "LOCKED"
            and public.get("candidate_count") == 1
            and public.get("imported_count") == 1
            and public.get("duplicate_count") == 0
            and public.get("non_imported_count") == 0
            and isinstance(public.get("recall_count"), int)
            and public.get("recall_count") >= 1
            and public.get("exact_imported_atom_recalled") is True
        ):
            out["status"] = "REAL_PRIVATE_CANDIDATE_CANARY_PASS"
            _emit(out)
            return 0

        out["status"] = "REAL_PRIVATE_CANDIDATE_CANARY_RESULT_REQUIRES_GPT_REVIEW"
        _emit(out)
        return 0

    except Exception:
        out["status"] = "REAL_PRIVATE_CANDIDATE_CANARY_EXECUTION_FAILED"
        out["LOCAL_EXECUTION_ISSUES"] = ["PRIVATE_CANARY_EXCEPTION_REDACTED"]
        _emit(out)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
