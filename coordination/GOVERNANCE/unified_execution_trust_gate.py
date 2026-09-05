"""Fresh canonical trust gate for process-start and carrier handoff.

Security boundary: Python object identity is never authority. Every authority-bearing
admission is re-attested against the trusted remote canonical main immediately before use.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping

try:
    from coordination.GOVERNANCE import unified_execution_validation as base
except ModuleNotFoundError:
    module_path = Path(__file__).with_name("unified_execution_validation.py")
    spec = importlib.util.spec_from_file_location("unified_execution_validation", module_path)
    if spec is None or spec.loader is None:
        raise
    base = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, base)
    spec.loader.exec_module(base)

ExecutionContractError = base.ExecutionContractError

_GLOBAL_POLICY = {
    "protocol_id": "UNIFIED-AGENT-EXECUTION-FABRIC-v1",
    "allowed_execution_carriers": sorted(base.GLOBAL_CARRIERS),
    "non_weakenable_invariants": sorted(base.NON_WEAKENABLE_INVARIANTS),
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


def _remote_main_sha(repo_path: str | Path) -> str:
    remote = base._run_git(
        repo_path,
        "ls-remote",
        base.TRUSTED_CONTROL_PLANE_URL,
        "refs/heads/main",
    )
    fields = remote.split()
    if len(fields) < 2 or not re.fullmatch(r"[0-9a-f]{40}", fields[0]):
        raise ExecutionContractError(
            "fresh_trust_gate: invalid trusted remote main identity"
        )
    return fields[0]


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
    return base._run_git(repo_path, "show", f"{sha}:{path}")


def _revalidate_project_adapter_at_sha(
    repo_path: str | Path, canonical: Mapping[str, Any]
) -> None:
    """Re-run the project-specific semantic floor on the exact authority main."""
    main_sha = str(canonical["canonical_main_sha"])
    project_id = canonical["project_id"]
    execution_repository = canonical["execution_repository"]
    matches: list[Mapping[str, Any]] = []

    for path in base.PROJECT_ADAPTER_PATHS:
        text = _read_at_sha(repo_path, main_sha, path)
        parsed = base.parse_and_validate_project_adapter(text, _GLOBAL_POLICY)
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


def _fresh_canonical_authority(
    repo_path: str | Path,
) -> base.VerifiedCanonicalAuthority:
    """Build, semantically revalidate, then terminally recheck remote main."""
    fresh = base.build_verified_canonical_authority(repo_path)
    canonical = _authority_mapping(fresh)

    # Structural receipt validation is useful, but it is not the trust decision.
    base.validate_canonical_authority(fresh)
    _revalidate_project_adapter_at_sha(repo_path, canonical)
    _terminal_remote_main_recheck(repo_path, str(canonical["canonical_main_sha"]))
    return fresh


def validate_canonical_authority(
    repo_path: str | Path, claimed_snapshot: base.VerifiedCanonicalAuthority
) -> base.VerifiedCanonicalAuthority:
    """Return a fresh canonical snapshot only when the claim exactly matches it.

    A direct constructor, internal factory call, issuer reuse, or dataclasses.replace()
    clone cannot create authority. The only trust root is the fresh remote-main readback.
    """
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
    """Authoritative process-start gate. Never launch from a cached object alone."""
    fresh = validate_canonical_authority(repo_path, claimed_snapshot)
    base.validate_local_admission(admission, dispatch, fresh)
    return fresh


def validate_process_start(
    repo_path: str | Path,
    admission: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    claimed_snapshot: base.VerifiedCanonicalAuthority,
) -> base.VerifiedCanonicalAuthority:
    """Sole governed process-start authority entrypoint."""
    return validate_local_admission(repo_path, admission, dispatch, claimed_snapshot)


def _fresh_release_witness(
    repo_path: str | Path, release_ref: str
) -> base.VerifiedReleaseWitness:
    fresh = base.build_verified_release_witness(repo_path, release_ref)
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
    """Fresh-gated carrier transfer.

    The old authority snapshot is historical evidence only. It cannot admit a writer.
    Current authority and current release evidence are independently rebuilt from the
    trusted remote main before the new writer can start.
    """
    fresh_new = validate_local_admission(
        repo_path, new_admission, new_dispatch, new_authority_snapshot
    )
    fresh_release = validate_release_witness(
        repo_path, release_ref, release_snapshot
    )
    if (
        _release_mapping(fresh_release)["canonical_main_sha"]
        != _authority_mapping(fresh_new)["canonical_main_sha"]
    ):
        raise ExecutionContractError(
            "fresh_trust_gate: release and new admission are from different main states"
        )

    # The base handoff validator still checks old snapshot/release binding, but only
    # the freshly rebuilt release and new authority can grant current execution.
    base.validate_carrier_handoff(
        handoff,
        old_dispatch,
        old_authority_snapshot,
        fresh_release,
        new_dispatch,
        new_admission,
        fresh_new,
    )
