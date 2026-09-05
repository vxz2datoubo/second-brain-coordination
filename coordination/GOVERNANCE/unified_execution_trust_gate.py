"""Fresh canonical trust gate for process-start and carrier handoff.

Security boundary: Python object identity and caller/user Git configuration are never
authority. Every authority-bearing admission is re-attested through a bridge-owned,
configuration-isolated canonical Git transport immediately before use.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys
from hashlib import sha256
from typing import Any, Mapping

try:
    from coordination.GOVERNANCE import unified_execution_validation as base
    from coordination.GOVERNANCE import unified_execution_trusted_transport as transport
except ModuleNotFoundError:
    base_path = Path(__file__).with_name("unified_execution_validation.py")
    base_spec = importlib.util.spec_from_file_location("unified_execution_validation", base_path)
    if base_spec is None or base_spec.loader is None:
        raise
    base = importlib.util.module_from_spec(base_spec)
    sys.modules.setdefault(base_spec.name, base)
    base_spec.loader.exec_module(base)

    transport_path = Path(__file__).with_name("unified_execution_trusted_transport.py")
    transport_spec = importlib.util.spec_from_file_location(
        "unified_execution_trusted_transport", transport_path
    )
    if transport_spec is None or transport_spec.loader is None:
        raise
    transport = importlib.util.module_from_spec(transport_spec)
    sys.modules.setdefault(transport_spec.name, transport)
    transport_spec.loader.exec_module(transport)

ExecutionContractError = base.ExecutionContractError

_GLOBAL_POLICY = {
    "protocol_id": "UNIFIED-AGENT-EXECUTION-FABRIC-v1",
    "allowed_execution_carriers": sorted(base.GLOBAL_CARRIERS),
    "non_weakenable_invariants": sorted(base.NON_WEAKENABLE_INVARIANTS),
}

_PROTECTED_ADAPTER_KEYS = {
    "project_id",
    "global_protocol_id",
    "inherits_global_invariants",
    "control_plane_repository",
    "execution_repository",
    "global_engineering_sync",
    "chat_history_is_sole_authority",
    "order_authority",
    "engineering_execution_does_not_imply_order_authority",
    "default_authority",
    "place_order_allowed",
    "project_baton_is_navigation_not_execution_authority",
    "ai_director_calls_require_explicit_adapter",
    "global_factory_rule",
    "source_authority",
    "second_brain_may_not_silently_modify_domain_truth",
    "engineering_model_choice_does_not_override",
    "authority",
    "allowed_execution_carriers",
    "tool_interfaces",
    "numeric_and_research_invariants",
    "hard_boundaries",
    "repositories",
    "canonical_entrypoints",
    "default_model_profiles",
    "collision_domains",
    "acceptance",
    "handoff",
}


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


def _same_snapshot(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return json.dumps(
        _normalize(left), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) == json.dumps(
        _normalize(right), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _authority_mapping(snapshot: Any) -> Mapping[str, Any]:
    if not isinstance(snapshot, base.VerifiedCanonicalAuthority):
        raise ExecutionContractError(
            "fresh_trust_gate: claimed authority must use the governed snapshot shape"
        )
    return snapshot.as_mapping()


def _release_mapping(snapshot: Any) -> Mapping[str, Any]:
    if not isinstance(snapshot, base.VerifiedReleaseWitness):
        raise ExecutionContractError(
            "fresh_trust_gate: claimed release must use the governed snapshot shape"
        )
    return snapshot.as_mapping()


def _protected_open(repo_path: str | Path):
    try:
        return transport.open_trusted_main(repo_path)
    except transport.TrustedTransportError as exc:
        raise ExecutionContractError(f"fresh_trust_gate: {exc}") from exc


def _remote_main_sha(repo_path: str | Path) -> str:
    try:
        return transport.remote_main_sha(repo_path)
    except transport.TrustedTransportError as exc:
        raise ExecutionContractError(f"fresh_trust_gate: {exc}") from exc


def _terminal_remote_main_recheck(
    repo_path: str | Path, expected_main_sha: str
) -> None:
    observed = _remote_main_sha(repo_path)
    if observed != expected_main_sha:
        raise ExecutionContractError(
            "fresh_trust_gate: canonical main moved before admission completed"
        )


def _read_at_sha(repo_path: str | Path, sha: str, path: str) -> str:
    base._validate_ref(path)
    observed, read = _protected_open(repo_path)
    if observed != sha:
        raise ExecutionContractError(
            "fresh_trust_gate: canonical main changed before exact-SHA adapter read"
        )
    return read(path).decode("utf-8")


def _reject_duplicate_top_level_yaml_keys(text: str) -> None:
    """Reject duplicate top-level adapter keys before regex-based semantic parsing.

    This prevents parser-differential ambiguity where this validator observes the first
    authority-bearing section while a standard YAML consumer may apply last-key-wins.
    """
    counts: dict[str, int] = {}
    for line in text.splitlines():
        if not line or line.startswith((" ", "\t")) or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_]+):", line)
        if not match:
            continue
        key = match.group(1)
        counts[key] = counts.get(key, 0) + 1
    duplicates = sorted(key for key, count in counts.items() if count > 1)
    if duplicates:
        raise ExecutionContractError(
            "fresh_trust_gate: duplicate top-level adapter YAML keys: "
            + ", ".join(duplicates)
        )


def _reject_duplicate_protected_yaml_keys(text: str) -> None:
    counts: dict[str, int] = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^\s*(?:-\s+)?([A-Za-z0-9_]+):", line)
        if not match:
            continue
        key = match.group(1)
        if key in _PROTECTED_ADAPTER_KEYS:
            counts[key] = counts.get(key, 0) + 1
    duplicates = sorted(key for key, count in counts.items() if count > 1)
    if duplicates:
        raise ExecutionContractError(
            "fresh_trust_gate: duplicate protected adapter YAML keys: "
            + ", ".join(duplicates)
        )


def _strict_parse_adapter(text: str) -> Mapping[str, Any]:
    _reject_duplicate_top_level_yaml_keys(text)
    _reject_duplicate_protected_yaml_keys(text)
    return base.parse_and_validate_project_adapter(text, _GLOBAL_POLICY)


def _revalidate_project_adapter_at_sha(
    repo_path: str | Path, canonical: Mapping[str, Any]
) -> None:
    main_sha = str(canonical["canonical_main_sha"])
    project_id = canonical["project_id"]
    execution_repository = canonical["execution_repository"]
    matches: list[Mapping[str, Any]] = []

    for path in base.PROJECT_ADAPTER_PATHS:
        text = _read_at_sha(repo_path, main_sha, path)
        parsed = _strict_parse_adapter(text)
        if parsed["project_id"] == project_id:
            matches.append(parsed)

    if len(matches) != 1:
        raise ExecutionContractError(
            "fresh_trust_gate: canonical project adapter did not resolve uniquely"
        )
    if matches[0]["execution_repository"] != execution_repository:
        raise ExecutionContractError(
            "fresh_trust_gate: execution repository differs from semantically "
            "validated project adapter"
        )


def _secure_build_verified_canonical_authority(
    repo_path: str | Path,
) -> base.VerifiedCanonicalAuthority:
    canonical_main_sha, read = _protected_open(repo_path)
    active_raw = read(base.ACTIVE_TASK_INDEX_REF)
    active = active_raw.decode("utf-8")
    refs = {
        "active_task_index_ref": base.ACTIVE_TASK_INDEX_REF,
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


def _secure_build_verified_release_witness(
    repo_path: str | Path, release_ref: str
) -> base.VerifiedReleaseWitness:
    base._validate_ref(release_ref)
    canonical_main_sha, read = _protected_open(repo_path)
    raw = read(release_ref)
    text = raw.decode("utf-8")
    required = (
        *base.COMMON_IDENTITY_FIELDS,
        "writer_lease_ref",
        "released_lease_digest",
        "writer_lease_identity",
        "release_status",
    )
    payload = {key: base._scalar(text, key) for key in required}
    if payload["control_plane_repository"] != base.TRUSTED_CONTROL_PLANE_REPOSITORY:
        raise ExecutionContractError("release_witness: wrong control-plane repository")
    if payload["release_status"] != "RELEASED":
        raise ExecutionContractError("release_witness: release document is not RELEASED")
    base._validate_ref(payload["writer_lease_ref"])
    computed_identity = base._writer_lease_identity(
        payload, payload["writer_lease_ref"], payload["released_lease_digest"]
    )
    if payload["writer_lease_identity"] != computed_identity:
        raise ExecutionContractError("release_witness: writer lease identity mismatch")
    payload["canonical_main_sha"] = canonical_main_sha
    payload["release_ref"] = release_ref
    payload["release_document_digest"] = base._sha(raw)
    payload["release_receipt_digest"] = base._json_digest(payload)
    return base._issue_release(payload)


def _fresh_canonical_authority(
    repo_path: str | Path,
) -> base.VerifiedCanonicalAuthority:
    fresh = _secure_build_verified_canonical_authority(repo_path)
    canonical = _authority_mapping(fresh)
    base.validate_canonical_authority(fresh)
    _revalidate_project_adapter_at_sha(repo_path, canonical)
    _terminal_remote_main_recheck(repo_path, str(canonical["canonical_main_sha"]))
    return fresh


def validate_canonical_authority(
    repo_path: str | Path, claimed_snapshot: base.VerifiedCanonicalAuthority
) -> base.VerifiedCanonicalAuthority:
    claimed = _authority_mapping(claimed_snapshot)
    fresh = _fresh_canonical_authority(repo_path)
    canonical = _authority_mapping(fresh)
    if not _same_snapshot(claimed, canonical):
        raise ExecutionContractError(
            "fresh_trust_gate: claimed authority differs from fresh canonical state"
        )
    return fresh


def validate_dispatch(
    repo_path: str | Path,
    dispatch: Mapping[str, Any],
    claimed_snapshot: base.VerifiedCanonicalAuthority,
) -> base.VerifiedCanonicalAuthority:
    fresh = validate_canonical_authority(repo_path, claimed_snapshot)
    base.validate_dispatch(dispatch, fresh)
    return fresh


def validate_local_admission(
    repo_path: str | Path,
    admission: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    claimed_snapshot: base.VerifiedCanonicalAuthority,
) -> base.VerifiedCanonicalAuthority:
    fresh = validate_canonical_authority(repo_path, claimed_snapshot)
    base.validate_local_admission(admission, dispatch, fresh)
    return fresh


def validate_process_start(
    repo_path: str | Path,
    admission: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    claimed_snapshot: base.VerifiedCanonicalAuthority,
) -> base.VerifiedCanonicalAuthority:
    return validate_local_admission(repo_path, admission, dispatch, claimed_snapshot)


def _fresh_release_witness(
    repo_path: str | Path, release_ref: str
) -> base.VerifiedReleaseWitness:
    fresh = _secure_build_verified_release_witness(repo_path, release_ref)
    release = _release_mapping(fresh)
    _terminal_remote_main_recheck(repo_path, str(release["canonical_main_sha"]))
    return fresh


def validate_release_witness(
    repo_path: str | Path,
    release_ref: str,
    claimed_snapshot: base.VerifiedReleaseWitness,
) -> base.VerifiedReleaseWitness:
    claimed = _release_mapping(claimed_snapshot)
    fresh = _fresh_release_witness(repo_path, release_ref)
    canonical = _release_mapping(fresh)
    if not _same_snapshot(claimed, canonical):
        raise ExecutionContractError(
            "fresh_trust_gate: claimed release differs from fresh canonical release"
        )
    return fresh


def validate_carrier_handoff(
    repo_path: str | Path,
    release_ref: str,
    handoff: Mapping[str, Any],
    old_dispatch: Mapping[str, Any],
    old_authority_snapshot: base.VerifiedCanonicalAuthority,
    release_snapshot: base.VerifiedReleaseWitness,
    new_dispatch: Mapping[str, Any],
    new_admission: Mapping[str, Any],
    new_authority_snapshot: base.VerifiedCanonicalAuthority,
) -> None:
    fresh_new = validate_local_admission(
        repo_path, new_admission, new_dispatch, new_authority_snapshot
    )
    fresh_release = validate_release_witness(repo_path, release_ref, release_snapshot)
    if (
        _release_mapping(fresh_release)["canonical_main_sha"]
        != _authority_mapping(fresh_new)["canonical_main_sha"]
    ):
        raise ExecutionContractError(
            "fresh_trust_gate: release and new admission are from different main states"
        )
    base.validate_carrier_handoff(
        handoff,
        old_dispatch,
        old_authority_snapshot,
        fresh_release,
        new_dispatch,
        new_admission,
        fresh_new,
    )