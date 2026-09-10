"""Governed, read-only binding for the canonical W4 experiment-family fixture.

This module deliberately has no caller-selected store, path, or write API.
The descriptor is a checked-in public-safe fixture; a fresh temporary SQLite
database is reconstructed for each resolution so the descriptor remains the
only trust root for this offline read surface.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from .registry import (Registry, RegistryError, canonical_json, digest, event_digest,
                       open_store, semantic_digest)

W4_READ_SURFACE_ID = "w4_experiment_family.registry.read_experiment_family"
W4_CONTRACT_VERSION = "1.0"
GOVERNED_DESCRIPTOR_REF = ("coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
                           "W4-STRATEGY-EXPERIMENT-FAMILY-P0/fixtures/canonical-store/"
                           "CANONICAL-W4-STORE.yaml")
GOVERNED_WORK_CLAIM_REF = ("coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
                           "CODEX-W4-CANONICAL-EXPERIMENT-FAMILY-READ-BINDING-R190/WORK-CLAIM.yaml")
GOVERNED_AUTH_WITNESS_REF = ("coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
                             "CODEX-W4-CANONICAL-EXPERIMENT-FAMILY-READ-BINDING-R190/AUTHORIZATION-WITNESS.yaml")
GOVERNED_TASK_ID = "CODEX-W4-CANONICAL-EXPERIMENT-FAMILY-READ-BINDING-R190"
GOVERNED_ROUTE_EPOCH = 190
GOVERNED_EXECUTOR_ROLE = "CODEX_STANDARD"
READ_SURFACE_CODE_REFS = [
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/W4-STRATEGY-EXPERIMENT-FAMILY-P0/src/w4_experiment_family/registry.py",
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/W4-STRATEGY-EXPERIMENT-FAMILY-P0/src/w4_experiment_family/read_binding.py",
]


class ReadVerificationState(str, Enum):
    CANONICAL_W4_READ_VERIFIED = "CANONICAL_W4_READ_VERIFIED"
    CANONICAL_W4_READ_VERIFIED_POINTER_ADVANCED = "CANONICAL_W4_READ_VERIFIED_POINTER_ADVANCED"
    W4_CANONICAL_STORE_UNRESOLVED = "W4_CANONICAL_STORE_UNRESOLVED"
    W4_SOURCE_PATH_ESCAPE = "W4_SOURCE_PATH_ESCAPE"
    W4_NONCANONICAL_SOURCE = "W4_NONCANONICAL_SOURCE"
    W4_STORE_IDENTITY_MISMATCH = "W4_STORE_IDENTITY_MISMATCH"
    W4_SOURCE_CONTENT_MISMATCH = "W4_SOURCE_CONTENT_MISMATCH"
    W4_EVENT_CHAIN_MISMATCH = "W4_EVENT_CHAIN_MISMATCH"
    W4_FAMILY_NOT_FOUND = "W4_FAMILY_NOT_FOUND"
    W4_REVISION_NOT_FOUND = "W4_REVISION_NOT_FOUND"
    W4_TRIAL_MANIFEST_DIGEST_MISMATCH = "W4_TRIAL_MANIFEST_DIGEST_MISMATCH"
    W4_SNAPSHOT_DIGEST_MISMATCH = "W4_SNAPSHOT_DIGEST_MISMATCH"
    W4_RECEIPT_DIGEST_MISMATCH = "W4_RECEIPT_DIGEST_MISMATCH"
    W4_READ_AUTHORIZATION_INVALID = "W4_READ_AUTHORIZATION_INVALID"
    W4_UNSUPPORTED_EVENT_SCHEMA = "W4_UNSUPPORTED_EVENT_SCHEMA"
    ABSTAIN = "ABSTAIN"


class ReadError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}{': ' + detail if detail else ''}")
        self.code = code


@dataclass(frozen=True)
class ReadAuthorization:
    task_id: str
    route_epoch: int
    executor_role: str
    work_claim_ref: str
    authorization_witness_ref: str


@dataclass(frozen=True)
class CanonicalW4StoreHandle:
    store_instance_id: str
    db_path: str
    descriptor_ref: str
    descriptor_sha256: str
    w4_contract_version: str
    store_schema_version: str
    canonical_ref: str
    canonical_main_sha: str
    canonical_main_sha_source: str
    family_id: str
    family_revision_id: str
    descriptor: dict[str, Any]


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "coordination").is_dir():
            return parent
    raise ReadError("W4_CANONICAL_STORE_UNRESOLVED", "repository root")


def _governed_path(root: Path, ref: str) -> Path:
    candidate = (root / ref).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ReadError("W4_SOURCE_PATH_ESCAPE") from exc
    return candidate


def _descriptor(root: Path) -> tuple[dict[str, Any], str]:
    path = _governed_path(root, GOVERNED_DESCRIPTOR_REF)
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))  # JSON is intentionally valid YAML.
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadError("W4_CANONICAL_STORE_UNRESOLVED", "descriptor") from exc
    if not isinstance(value, dict) or value.get("schema") != "CanonicalW4StoreDescriptor/v1":
        raise ReadError("W4_CANONICAL_STORE_UNRESOLVED", "descriptor schema")
    required = ("repository", "store_instance_id", "w4_contract_version", "store_schema_version",
                "canonical_ref_pin", "read_surface_id", "family_id", "family_revision_id", "events")
    if any(key not in value for key in required) or not isinstance(value["events"], list):
        raise ReadError("W4_CANONICAL_STORE_UNRESOLVED", "descriptor fields")
    return value, hashlib.sha256(raw).hexdigest()


def _canonical_main_sha(root: Path) -> tuple[str, str]:
    for ref, source in (("refs/heads/main", "git:refs/heads/main"),
                        ("refs/remotes/origin/main", "git:refs/remotes/origin/main"),
                        ("HEAD", "git:HEAD")):
        try:
            result = subprocess.run(["git", "-C", str(root), "rev-parse", ref],
                                    check=True, capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            continue
        sha = result.stdout.strip()
        if re.fullmatch(r"[0-9a-f]{40}", sha) is not None:
            return sha, source
    raise ReadError("W4_CANONICAL_STORE_UNRESOLVED", "canonical main")


def resolve_canonical_w4_store_v1() -> CanonicalW4StoreHandle:
    """Resolve only the module-owned descriptor and reconstruct its event store."""
    root = _repo_root()
    descriptor, descriptor_sha = _descriptor(root)
    if (descriptor["repository"] != "vxz2datoubo/second-brain-coordination" or
            descriptor["w4_contract_version"] != W4_CONTRACT_VERSION or
            descriptor["store_schema_version"] != "v1" or
            descriptor["canonical_ref_pin"] != "refs/heads/main" or
            descriptor["read_surface_id"] != W4_READ_SURFACE_ID):
        raise ReadError("W4_CANONICAL_STORE_UNRESOLVED", "governed identity")
    db_path = str(Path(tempfile.mkdtemp(prefix="governed-w4-store-")) / "canonical.sqlite3")
    store = open_store(db_path)
    previous: str | None = None
    try:
        for expected_sequence, item in enumerate(descriptor["events"]):
            if not isinstance(item, dict):
                raise ReadError("W4_UNSUPPORTED_EVENT_SCHEMA")
            store.append(family_id=descriptor["family_id"], family_revision_id=descriptor["family_revision_id"],
                         expected_sequence=expected_sequence, expected_previous_digest=previous,
                         event_id=item["event_id"], idempotency_key=item["idempotency_key"],
                         event_type=item["event_type"], payload=item["payload"])
            previous = store.read_family_event_stream(descriptor["family_id"], descriptor["family_revision_id"])[-1]["event_digest"]
    except (KeyError, TypeError, RegistryError) as exc:
        raise ReadError("W4_CANONICAL_STORE_UNRESOLVED", "event replay") from exc
    finally:
        store.db.close()
    sha, source = _canonical_main_sha(root)
    return CanonicalW4StoreHandle(descriptor["store_instance_id"], db_path, GOVERNED_DESCRIPTOR_REF,
                                  descriptor_sha, descriptor["w4_contract_version"],
                                  descriptor["store_schema_version"], descriptor["canonical_ref_pin"],
                                  sha, source, descriptor["family_id"],
                                  descriptor["family_revision_id"], descriptor)


def _scalar_yaml(root: Path, ref: str) -> dict[str, str]:
    path = _governed_path(root, ref)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ReadError("W4_READ_AUTHORIZATION_INVALID") from exc
    values: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*):\s*(?:\"([^\"]*)\"|'([^']*)'|([^#\s]+))\s*(?:#.*)?", line)
        if match:
            values[match.group(1)] = next(value for value in match.groups()[1:] if value is not None)
    return values


def _authorization_valid(authorization: Any) -> bool:
    if not isinstance(authorization, ReadAuthorization):
        return False
    if (authorization.task_id != GOVERNED_TASK_ID or authorization.route_epoch != GOVERNED_ROUTE_EPOCH or
            authorization.executor_role != GOVERNED_EXECUTOR_ROLE or
            authorization.work_claim_ref != GOVERNED_WORK_CLAIM_REF or
            authorization.authorization_witness_ref != GOVERNED_AUTH_WITNESS_REF):
        return False
    try:
        root = _repo_root()
        claim = _scalar_yaml(root, GOVERNED_WORK_CLAIM_REF)
        witness = _scalar_yaml(root, GOVERNED_AUTH_WITNESS_REF)
    except ReadError:
        return False
    expected = {"task_id": GOVERNED_TASK_ID, "route_epoch": str(GOVERNED_ROUTE_EPOCH),
                "executor": GOVERNED_EXECUTOR_ROLE, "execution_allowed": "true"}
    return all(claim.get(key) == value and witness.get(key) == value for key, value in expected.items())


def _read_only_connection(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(Path(db_path).as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _head(connection: sqlite3.Connection, family_id: str, revision: str) -> tuple[Any, ...] | None:
    row = connection.execute("SELECT family_id,family_revision_id,family_sequence,event_id,event_digest FROM experiment_events WHERE family_id=? AND family_revision_id=? ORDER BY family_sequence DESC LIMIT 1", (family_id, revision)).fetchone()
    count = connection.execute("SELECT COUNT(*) FROM experiment_events WHERE family_id=? AND family_revision_id=?", (family_id, revision)).fetchone()[0]
    return None if row is None else tuple(row) + (count,)


def _verify_rows(rows: list[sqlite3.Row], family_id: str, revision: str) -> None:
    previous = None
    for sequence, row in enumerate(rows, 1):
        if row["family_sequence"] != sequence or row["previous_event_digest"] != previous:
            raise ReadError("W4_EVENT_CHAIN_MISMATCH")
        semantic = semantic_digest(row["event_type"], json.loads(row["record_json"]))
        actual = event_digest(family_id=family_id, family_revision_id=revision, family_sequence=sequence,
                              event_id=row["event_id"], idempotency_key=row["idempotency_key"],
                              event_type=row["event_type"], semantic_digest=semantic,
                              previous_event_digest=previous)
        if semantic != row["semantic_digest"] or actual != row["event_digest"]:
            raise ReadError("W4_EVENT_CHAIN_MISMATCH")
        previous = actual


def _stable_read(handle: CanonicalW4StoreHandle) -> tuple[dict[str, Any], list[sqlite3.Row], tuple[Any, ...], bool]:
    conn = _read_only_connection(handle.db_path)
    try:
        conn.execute("BEGIN")
        before = _head(conn, handle.family_id, handle.family_revision_id)
        if before is None:
            raise ReadError("W4_FAMILY_NOT_FOUND")
        rows = list(conn.execute("SELECT * FROM experiment_events WHERE family_id=? AND family_revision_id=? ORDER BY family_sequence", (handle.family_id, handle.family_revision_id)))
        _verify_rows(rows, handle.family_id, handle.family_revision_id)
        reader = object.__new__(Registry)
        reader.db = conn
        snapshot = reader.reduce_family_snapshot(handle.family_id, handle.family_revision_id)
        if _head(conn, handle.family_id, handle.family_revision_id) != before:
            raise ReadError("W4_SOURCE_CONTENT_MISMATCH", "head changed during read")
        conn.execute("COMMIT")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    post = _read_only_connection(handle.db_path)
    try:
        advanced = _head(post, handle.family_id, handle.family_revision_id) != before
    finally:
        post.close()
    return snapshot, rows, before, advanced


def _code_digest(root: Path) -> str:
    material = hashlib.sha256()
    for ref in READ_SURFACE_CODE_REFS:
        material.update(ref.encode("utf-8") + b"\0")
        material.update(_governed_path(root, ref).read_bytes())
    return material.hexdigest()


def _observation_time(value: str | None) -> str:
    if value is not None:
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z", value):
            raise ReadError("W4_READ_AUTHORIZATION_INVALID", "observed_at")
        return value
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _authority() -> dict[str, bool]:
    return {"w4_strategy_experiment_write_authority": False, "trial_ledger_authority": False,
            "backtest_result_authority": False, "market_data_truth_authority": False,
            "w7_validation_authority": False, "probability_authority": False,
            "risk_authority": False, "position_authority": False, "order_authority": False,
            "trade_authority": False, "read_evidence_authority": True}


def _receipt(handle: CanonicalW4StoreHandle, snapshot: Mapping[str, Any], rows: list[sqlite3.Row],
             head: tuple[Any, ...], advanced: bool, authorization: ReadAuthorization, observed: str) -> dict[str, Any]:
    family = json.loads(rows[0]["record_json"])
    state = Registry.reduce_rows(rows)
    manifest = dict(sorted(state["manifest"].items()))
    root = _repo_root()
    value: dict[str, Any] = {
        "schema": "CanonicalExperimentFamilyReadReceipt/v1", "receipt_version": "P0",
        "repository": handle.descriptor["repository"], "canonical_main_sha": handle.canonical_main_sha,
        "canonical_main_sha_source": handle.canonical_main_sha_source,
        "canonical_source_kind": "GOVERNED_W4_SQLITE_STORE", "canonical_ref": handle.canonical_ref,
        "source_is_on_canonical_lineage": True, "store_instance_id": handle.store_instance_id,
        "store_schema_version": handle.store_schema_version, "w4_contract_version": handle.w4_contract_version,
        "w4_read_surface_id": W4_READ_SURFACE_ID, "w4_read_surface_code_digest": _code_digest(root),
        "experiment_family_ref": f"{handle.family_id}@{handle.family_revision_id}", "family_id": handle.family_id,
        "family_revision_id": handle.family_revision_id, "snapshot_sequence": head[2],
        "w4_source_content_sha256": handle.descriptor_sha256,
        "provenance_state": "CANONICAL_COMPLETE" if snapshot["completeness_state"] == "COMPLETE" else "INCOMPLETE",
        "family_content_digest": snapshot["family_snapshot_digest"],
        "registered_family_digest": snapshot["registered_family_digest"],
        "expected_trial_manifest_digest": digest(manifest),
        "trial_id_set_digest": digest(sorted(manifest)), "trial_count": len(snapshot["trials"]),
        "ledger_head_digest": head[4], "ledger_head_sequence": head[2], "ledger_event_count": head[5],
        "ordered_event_digest_manifest_digest": digest([row["event_digest"] for row in rows]),
        "event_chain_verified": True, "transaction_read_consistent": True,
        "pointer_after_read_advanced": advanced, "selection_rule_ref": snapshot["selection_rule_ref"],
        "benchmark_ref": family["benchmark_ref"], "metric_id": family["metric_id"],
        "horizon_id": family["horizon_id"], "search_space_ref": family["search_space_ref"],
        "selected_trial_id": snapshot["selected_trial_id"], "task_id": authorization.task_id,
        "route_epoch": authorization.route_epoch, "executor_role": authorization.executor_role,
        "work_claim_ref": authorization.work_claim_ref,
        "authorization_witness_ref": authorization.authorization_witness_ref,
        "authorization_refs_verified": True, "read_at": observed, "as_of": observed,
        "runtime_code_digest": _code_digest(root), "authority": _authority(),
    }
    value["receipt_digest"] = digest(value)
    return value


def read_canonical_family(family_id: str, family_revision_id: str, *, authorization: ReadAuthorization,
                          observed_at: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    if not _authorization_valid(authorization):
        raise ReadError("W4_READ_AUTHORIZATION_INVALID")
    handle = resolve_canonical_w4_store_v1()
    if family_id != handle.family_id or family_revision_id != handle.family_revision_id:
        raise ReadError("W4_NONCANONICAL_SOURCE")
    snapshot, rows, head, advanced = _stable_read(handle)
    return snapshot, _receipt(handle, snapshot, rows, head, advanced, authorization, _observation_time(observed_at))


def _result(state: str, primary: str, detail: Mapping[str, Any] | None = None, advanced: bool = False) -> dict[str, Any]:
    return {"verification_state": state, "primary": primary, "detail": dict(detail or {}),
            "pointer_advanced_after_read": advanced}


def verify_canonical_family_receipt(receipt: Any, *, snapshot: Mapping[str, Any] | None = None,
                                    observed_at: str | None = None) -> dict[str, Any]:
    """Verify a receipt from governed provenance, never from caller-supplied source state."""
    if not isinstance(receipt, Mapping):
        return _result("W4_READ_AUTHORIZATION_INVALID", "W4_READ_AUTHORIZATION_INVALID")
    try:
        auth = ReadAuthorization(receipt.get("task_id"), receipt.get("route_epoch"),
                                 receipt.get("executor_role"), receipt.get("work_claim_ref"),
                                 receipt.get("authorization_witness_ref"))
    except TypeError:
        return _result("W4_READ_AUTHORIZATION_INVALID", "W4_READ_AUTHORIZATION_INVALID")
    if not receipt.get("authorization_refs_verified") or not _authorization_valid(auth):
        return _result("W4_READ_AUTHORIZATION_INVALID", "W4_READ_AUTHORIZATION_INVALID")
    try:
        handle = resolve_canonical_w4_store_v1()
    except ReadError as exc:
        return _result(exc.code, exc.code)
    if receipt.get("canonical_ref") != "refs/heads/main" or receipt.get("source_is_on_canonical_lineage") is not True:
        return _result("W4_NONCANONICAL_SOURCE", "W4_NONCANONICAL_SOURCE")
    identity = {"repository": handle.descriptor["repository"], "canonical_main_sha": handle.canonical_main_sha,
                "canonical_main_sha_source": handle.canonical_main_sha_source, "store_instance_id": handle.store_instance_id,
                "store_schema_version": handle.store_schema_version, "w4_contract_version": handle.w4_contract_version,
                "w4_read_surface_id": W4_READ_SURFACE_ID, "family_id": handle.family_id,
                "family_revision_id": handle.family_revision_id,
                "experiment_family_ref": f"{handle.family_id}@{handle.family_revision_id}"}
    if any(receipt.get(key) != value for key, value in identity.items()):
        return _result("W4_STORE_IDENTITY_MISMATCH", "W4_STORE_IDENTITY_MISMATCH")
    if receipt.get("w4_source_content_sha256") != handle.descriptor_sha256:
        return _result("W4_SOURCE_CONTENT_MISMATCH", "W4_SOURCE_CONTENT_MISMATCH")
    try:
        rebuilt, rows, head, advanced = _stable_read(handle)
    except ReadError as exc:
        return _result(exc.code, exc.code)
    if receipt.get("family_content_digest") != rebuilt["family_snapshot_digest"] or (snapshot is not None and snapshot.get("family_snapshot_digest") != rebuilt["family_snapshot_digest"]):
        return _result("W4_SNAPSHOT_DIGEST_MISMATCH", "W4_SNAPSHOT_DIGEST_MISMATCH")
    state = Registry.reduce_rows(rows)
    manifest = dict(sorted(state["manifest"].items()))
    expected = {"expected_trial_manifest_digest": digest(manifest), "trial_id_set_digest": digest(sorted(manifest)),
                "registered_family_digest": rebuilt["registered_family_digest"],
                "trial_count": len(rebuilt["trials"])}
    if any(receipt.get(key) != value for key, value in expected.items()):
        return _result("W4_TRIAL_MANIFEST_DIGEST_MISMATCH", "W4_TRIAL_MANIFEST_DIGEST_MISMATCH")
    source = {"snapshot_sequence": head[2], "ledger_head_digest": head[4], "ledger_head_sequence": head[2],
              "ledger_event_count": head[5], "ordered_event_digest_manifest_digest": digest([row["event_digest"] for row in rows]),
              "event_chain_verified": True, "transaction_read_consistent": True,
              "w4_read_surface_code_digest": _code_digest(_repo_root()), "runtime_code_digest": _code_digest(_repo_root())}
    if any(receipt.get(key) != value for key, value in source.items()):
        return _result("W4_RECEIPT_DIGEST_MISMATCH", "W4_RECEIPT_DIGEST_MISMATCH")
    expected_digest = dict(receipt); supplied = expected_digest.pop("receipt_digest", None)
    if supplied != digest(expected_digest):
        return _result("W4_RECEIPT_DIGEST_MISMATCH", "W4_RECEIPT_DIGEST_MISMATCH")
    if observed_at is not None:
        try:
            _observation_time(observed_at)
        except ReadError:
            return _result("ABSTAIN", "ABSTAIN")
    state_name = "CANONICAL_W4_READ_VERIFIED_POINTER_ADVANCED" if advanced else "CANONICAL_W4_READ_VERIFIED"
    return _result(state_name, state_name, advanced=advanced)
