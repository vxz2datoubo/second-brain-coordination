"""Registered multi-task authority discovery for the unified execution fabric.

This module extends the canonical fresh trust gate without weakening it. It never
accepts arbitrary task-index paths from callers: every index must be registered in
trusted canonical main, and every selected index is revalidated through the same
full Route -> Claim -> Lease -> Reservation -> Prewrite -> Batch semantic chain.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from coordination.EXECUTION import canonical_write_paths as write_paths
from coordination.GOVERNANCE import unified_execution_trust_gate as gate

base = gate.base
ExecutionContractError = base.ExecutionContractError

REGISTRY_REF = "coordination/EXECUTION/ACTIVE-TASK-INDEX-REGISTRY.json"
REGISTRY_SCHEMA = "UNIFIED_ACTIVE_TASK_INDEX_REGISTRY/v1"
LEGACY_DEFAULT_REF = base.ACTIVE_TASK_INDEX_REF


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ExecutionContractError(
                f"active_task_registry: duplicate JSON key: {key}"
            )
        result[key] = value
    return result


def _parse_registry(raw: bytes) -> tuple[str, ...]:
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except ExecutionContractError:
        raise
    except Exception as exc:
        raise ExecutionContractError(
            "active_task_registry: registry is not valid duplicate-safe JSON"
        ) from exc

    if not isinstance(data, Mapping):
        raise ExecutionContractError("active_task_registry: root must be an object")
    if data.get("schema") != REGISTRY_SCHEMA:
        raise ExecutionContractError("active_task_registry: unsupported schema")
    if data.get("control_plane_repository") != base.TRUSTED_CONTROL_PLANE_REPOSITORY:
        raise ExecutionContractError("active_task_registry: wrong control-plane repository")
    if data.get("registry_status") != "ACTIVE":
        raise ExecutionContractError("active_task_registry: registry is not ACTIVE")

    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ExecutionContractError("active_task_registry: entries must be non-empty")

    refs: list[str] = []
    legacy_defaults = 0
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ExecutionContractError("active_task_registry: entry must be an object")
        if entry.get("status") != "REGISTERED":
            raise ExecutionContractError("active_task_registry: entry is not REGISTERED")
        ref = entry.get("active_task_index_ref")
        if not isinstance(ref, str) or not ref:
            raise ExecutionContractError("active_task_registry: missing task index ref")
        base._validate_ref(ref)
        if not ref.startswith("coordination/"):
            raise ExecutionContractError(
                "active_task_registry: task index must remain under coordination/"
            )
        refs.append(ref)
        if entry.get("legacy_default") is True:
            legacy_defaults += 1
            if ref != LEGACY_DEFAULT_REF:
                raise ExecutionContractError(
                    "active_task_registry: legacy_default points at non-legacy index"
                )

    if len(refs) != len(set(refs)):
        raise ExecutionContractError("active_task_registry: duplicate task index ref")
    if legacy_defaults != 1 or LEGACY_DEFAULT_REF not in refs:
        raise ExecutionContractError(
            "active_task_registry: legacy ACTIVE-WORKBUDDY-TASK must remain registered exactly once"
        )
    return tuple(refs)


def registered_task_index_refs(repo_path: str | Path) -> tuple[str, tuple[str, ...]]:
    canonical_main_sha, read = gate._protected_open(repo_path)
    refs = _parse_registry(read(REGISTRY_REF))
    gate._terminal_remote_main_recheck(repo_path, canonical_main_sha)
    return canonical_main_sha, refs


def _canonicalize_authorized_paths(paths: Sequence[str]) -> list[str]:
    try:
        return list(write_paths.canonicalize_authorized_paths(paths))
    except write_paths.CanonicalWritePathError as exc:
        raise ExecutionContractError(
            f"active_task_registry: non-canonical write surface: {exc}"
        ) from exc


def _build_authority_from_open(
    canonical_main_sha: str,
    read,
    active_task_index_ref: str,
) -> base.VerifiedCanonicalAuthority:
    active_raw = read(active_task_index_ref)
    active = active_raw.decode("utf-8")
    refs = {
        "active_task_index_ref": active_task_index_ref,
        "canonical_route_ref": base._scalar(active, "canonical_route"),
        "work_claim_ref": base._scalar(active, "work_claim"),
        "task_lease_ref": base._scalar(active, "task_lease"),
        "executor_reservation_ref": base._scalar(active, "executor_reservation"),
        "prewrite_snapshot_ref": base._scalar(active, "prewrite_snapshot"),
        "executable_batch_ref": base._scalar(active, "executable_batch"),
    }
    for path in refs.values():
        base._validate_ref(path)
    raw_docs = {name: read(path) for name, path in refs.items()}
    digests = {name: base._sha(data) for name, data in raw_docs.items()}
    route = raw_docs["canonical_route_ref"].decode("utf-8")
    claim = raw_docs["work_claim_ref"].decode("utf-8")
    lease = raw_docs["task_lease_ref"].decode("utf-8")
    reservation = raw_docs["executor_reservation_ref"].decode("utf-8")
    prewrite = raw_docs["prewrite_snapshot_ref"].decode("utf-8")
    task_id = base._scalar(active, "task_id")
    route_epoch = base._scalar(active, "route_epoch")
    branch = base._scalar(active, "implementation_branch")
    exact_base_sha = base._nested_scalar(active, "source_checkpoint", "exact_head")
    canonical_project_key = base._scalar(route, "project")
    project_id, execution_repository = base._resolve_project(read, canonical_project_key)
    authorized_paths = base._validate_authority_chain_semantics(
        active,
        route,
        claim,
        lease,
        reservation,
        prewrite,
        raw_docs["executable_batch_ref"],
        refs,
        task_id=task_id,
        route_epoch=route_epoch,
        branch=branch,
        exact_base_sha=exact_base_sha,
        canonical_project_key=canonical_project_key,
    )
    authorized_paths = _canonicalize_authorized_paths(authorized_paths)
    collision_domain = "WRITESET_SHA256:" + sha256(
        json.dumps(sorted(authorized_paths), separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    common_identity = {
        "control_plane_repository": base.TRUSTED_CONTROL_PLANE_REPOSITORY,
        "execution_repository": execution_repository,
        "project_id": project_id,
        "task_id": task_id,
        "route_epoch": route_epoch,
        "exact_base_sha": exact_base_sha,
        "implementation_branch": branch,
        "collision_domain": collision_domain,
    }
    writer_lease_identity = base._writer_lease_identity(
        common_identity, refs["task_lease_ref"], digests["task_lease_ref"]
    )
    denials = sorted(
        set(
            base._list(active, "hard_boundaries")
            + base._list(claim, "hard_boundaries")
            + ["NO_DIRECT_MAIN_WRITE", "NO_SELF_REVIEW", "NO_SELF_MERGE"]
        )
    )
    grants = ["EXECUTE_TASK"]
    if authorized_paths:
        grants.append("WRITE_AUTHORIZED_PATHS")
    payload: dict[str, Any] = {
        **common_identity,
        "canonical_main_sha": canonical_main_sha,
        "authority_refs": refs,
        "authority_digests": digests,
        "route_status": "READY",
        "execution_allowed": True,
        "fresh_readback": True,
        "authorized_paths": authorized_paths,
        "authority_grants": grants,
        "authority_denials": denials,
        "writer_lease_identity": writer_lease_identity,
    }
    receipt_material = {
        key: payload[key]
        for key in (
            *base.COMMON_IDENTITY_FIELDS,
            "canonical_main_sha",
            "authority_refs",
            "authority_digests",
            "route_status",
            "execution_allowed",
            "authorized_paths",
            "authority_grants",
            "authority_denials",
            "writer_lease_identity",
        )
    }
    payload["authority_chain_receipt_digest"] = base._json_digest(receipt_material)
    return base._issue_authority(payload)


def build_verified_canonical_authority_for_task_index(
    repo_path: str | Path, active_task_index_ref: str
) -> base.VerifiedCanonicalAuthority:
    base._validate_ref(active_task_index_ref)
    canonical_main_sha, read = gate._protected_open(repo_path)
    registered = _parse_registry(read(REGISTRY_REF))
    if active_task_index_ref not in registered:
        raise ExecutionContractError(
            "active_task_registry: caller-selected task index is not registered in canonical main"
        )
    fresh = _build_authority_from_open(
        canonical_main_sha, read, active_task_index_ref
    )
    canonical = fresh.as_mapping()
    base.validate_canonical_authority(fresh)
    gate._revalidate_project_adapter_at_sha(repo_path, canonical)
    gate._terminal_remote_main_recheck(repo_path, canonical_main_sha)
    return fresh


def _write_pattern(path: str) -> tuple[str, bool, bool]:
    """Return a canonical (root, recursive_tree, ambiguous_pattern) tuple."""
    try:
        root, recursive = write_paths.parse_write_pattern(path)
    except write_paths.CanonicalWritePathError as exc:
        raise ExecutionContractError(
            f"active_task_registry: non-canonical write surface: {exc}"
        ) from exc
    return root, recursive, False


def _write_paths_may_overlap(left: str, right: str) -> bool:
    lroot, ltree, lambiguous = _write_pattern(left)
    rroot, rtree, rambiguous = _write_pattern(right)
    if lambiguous or rambiguous or not lroot or not rroot:
        return True
    if lroot == rroot:
        return True
    if ltree and (rroot.startswith(lroot + "/")):
        return True
    if rtree and (lroot.startswith(rroot + "/")):
        return True
    return False


def _authority_write_surfaces_overlap(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> bool:
    left_paths = left.get("authorized_paths")
    right_paths = right.get("authorized_paths")
    if not isinstance(left_paths, (list, tuple)) or not isinstance(
        right_paths, (list, tuple)
    ):
        return True
    if not left_paths or not right_paths:
        return True
    canonical_left = _canonicalize_authorized_paths(left_paths)
    canonical_right = _canonicalize_authorized_paths(right_paths)
    if left["execution_repository"] != right["execution_repository"]:
        return False
    return any(
        _write_paths_may_overlap(lpath, rpath)
        for lpath in canonical_left
        for rpath in canonical_right
    )


def _build_registered_authority_set(
    repo_path: str | Path,
    observed_main: str,
    refs: Sequence[str],
) -> tuple[base.VerifiedCanonicalAuthority, ...]:
    authorities: list[base.VerifiedCanonicalAuthority] = []
    seen_task_identity: set[tuple[str, Any]] = set()
    seen_collision: set[tuple[str, str]] = set()
    seen_branch: set[tuple[str, str]] = set()

    for ref in refs:
        authority = build_verified_canonical_authority_for_task_index(repo_path, ref)
        current = authority.as_mapping()
        if current["canonical_main_sha"] != observed_main:
            raise ExecutionContractError(
                "active_task_registry: canonical main moved while enumerating tasks"
            )
        paths = current.get("authorized_paths")
        if not isinstance(paths, (list, tuple)):
            raise ExecutionContractError(
                "active_task_registry: authority has malformed authorized_paths"
            )
        _canonicalize_authorized_paths(paths)

        task_identity = (str(current["task_id"]), current["route_epoch"])
        if task_identity in seen_task_identity:
            raise ExecutionContractError(
                "active_task_registry: duplicate active task identity"
            )
        seen_task_identity.add(task_identity)

        execution_repository = str(current["execution_repository"])
        collision = (
            execution_repository,
            str(current["collision_domain"]),
        )
        if collision in seen_collision:
            raise ExecutionContractError(
                "active_task_registry: simultaneous active writers share a collision domain"
            )

        branch_identity = (
            execution_repository,
            str(current["implementation_branch"]),
        )
        if branch_identity in seen_branch:
            raise ExecutionContractError(
                "active_task_registry: simultaneous active writers share an implementation branch"
            )

        for existing in authorities:
            if _authority_write_surfaces_overlap(existing.as_mapping(), current):
                raise ExecutionContractError(
                    "active_task_registry: simultaneous active writer surfaces overlap or are ambiguous"
                )

        seen_collision.add(collision)
        seen_branch.add(branch_identity)
        authorities.append(authority)

    return tuple(authorities)


def build_registered_authorities(
    repo_path: str | Path,
) -> tuple[base.VerifiedCanonicalAuthority, ...]:
    observed_main, refs = registered_task_index_refs(repo_path)
    return _build_registered_authority_set(repo_path, observed_main, refs)


def validate_process_start_for_task_index(
    repo_path: str | Path,
    active_task_index_ref: str,
    admission: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    claimed_snapshot: base.VerifiedCanonicalAuthority,
) -> base.VerifiedCanonicalAuthority:
    """Fresh-gated process start for one explicitly registered task index.

    Process start is admitted only from a fresh registry-wide conflict-free authority
    set. The selected task must be registered on the same canonical main as every
    peer authority, and the caller snapshot must exactly match that fresh target.
    """
    base._validate_ref(active_task_index_ref)
    observed_main, refs = registered_task_index_refs(repo_path)
    if active_task_index_ref not in refs:
        raise ExecutionContractError(
            "active_task_registry: caller-selected task index is not registered in canonical main"
        )

    authorities = _build_registered_authority_set(repo_path, observed_main, refs)
    selected = authorities[refs.index(active_task_index_ref)]
    canonical = gate._authority_mapping(selected)
    if canonical["canonical_main_sha"] != observed_main:
        raise ExecutionContractError(
            "active_task_registry: selected authority is not bound to registry main"
        )

    claimed = gate._authority_mapping(claimed_snapshot)
    if not gate._same_snapshot(claimed, canonical):
        raise ExecutionContractError(
            "active_task_registry: claimed authority differs from fresh registered task authority"
        )
    base.validate_local_admission(admission, dispatch, selected)
    return selected


def build_legacy_default_authority(
    repo_path: str | Path,
) -> base.VerifiedCanonicalAuthority:
    return build_verified_canonical_authority_for_task_index(
        repo_path, LEGACY_DEFAULT_REF
    )
