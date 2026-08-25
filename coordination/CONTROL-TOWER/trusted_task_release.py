from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import importlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Mapping, Sequence

from control_tower import load_yaml, scan_repository
from lane_claims import (
    ACTIVE_IMPLEMENTATION,
    RESERVED_IMPLEMENTATION_NON_EXECUTABLE,
    CLAIMS_FILE,
    validate_claims,
)
from task_release_impact import ImpactGateError, evaluate_release_candidate


PROPOSAL_SCHEMA = "TaskReleaseProposal/v1"
TRUSTED_RECEIPT_SCHEMA = "TrustedTaskReleaseImpactReceipt/v1"
COORDINATOR_REPOSITORY = "vxz2datoubo/second-brain-coordination"
GPT_WORKERS_REGISTRY = "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
PROGRAM_CONTROL_TOWER = "coordination/PROGRAM-CONTROL-TOWER.md"
R145_S0E_SRC = (
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
    "GLOBAL-SIGNAL-PLANE/S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY/src"
)
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_ACTIVE_WORK_STATES = frozenset({ACTIVE_IMPLEMENTATION, RESERVED_IMPLEMENTATION_NON_EXECUTABLE})
_COLLISION_FIELDS = (
    "write_paths",
    "read_paths",
    "interfaces",
    "read_domains",
    "write_domains",
    "authority_claims",
)
_TRUSTED_CALLER_FIELDS = frozenset(
    {
        "observations",
        "authority_binding",
        "existing_work_items",
        "domain_binding",
        "collision_analysis",
        "final_disposition",
        "trusted_context",
    }
)
_PROPOSAL_FIELDS = frozenset(
    {
        "schema_version",
        "release_candidate_id",
        "source_signal_refs",
        "signal_primary_domain",
        "desired_effect",
        "proposed_target_domain",
        "proposed_write_surface",
        "materiality",
        "risk",
        "out_of_scope",
        "capability_inventory",
        "relations",
        "reverse_consumers",
        "consumer_inventory_complete",
        "composition",
        "synchronized_change_set",
        "regression_revalidation_set",
        "unaffected_set",
        "unresolved_unknowns",
    }
)
_DOMAIN_BINDING_SEAL = object()


class TrustedReleaseError(ValueError):
    """Stable fail-closed error for the R150 repository-bound integration seam."""

    def __init__(self, code: str, path: str = "/") -> None:
        super().__init__(code)
        self.code = code
        self.path = path


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise TrustedReleaseError("TRUSTED_GIT_OBSERVATION_FAILED")
    return result.stdout.strip()


def _head(root: Path) -> str:
    value = _git(root, "rev-parse", "HEAD")
    if not _SHA40.fullmatch(value):
        raise TrustedReleaseError("TRUSTED_HEAD_INVALID")
    return value


def _is_untracked_python_bytecode(status_line: str) -> bool:
    if not status_line.startswith("?? "):
        return False
    path = status_line[3:].replace("\\", "/")
    return "/__pycache__/" in f"/{path}" and path.endswith((".pyc", ".pyo"))


def _worktree_clean(root: Path) -> bool:
    output = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if not output:
        return True
    for line in output.splitlines():
        if not _is_untracked_python_bytecode(line):
            return False
    return True


def _exact_path_ref(root: Path, head: str, path: str) -> str:
    blob = _git(root, "rev-parse", f"{head}:{path}")
    if not _SHA40.fullmatch(blob):
        raise TrustedReleaseError("TRUSTED_PATH_BLOB_INVALID", f"/{path}")
    return f"git://{COORDINATOR_REPOSITORY}@{head}/{path}#blob={blob}"


def _load_r145_api(root: Path) -> tuple[Any, Any]:
    """Load the canonical R145 package without requiring ambient PYTHONPATH state."""
    src = (root / R145_S0E_SRC).resolve()
    if not src.is_dir():
        raise TrustedReleaseError("R145_CANONICAL_API_SOURCE_MISSING")
    original_path = list(sys.path)
    original_dont_write = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(src))
        module = importlib.import_module("global_signal_gateway.domain_authority")
    except (ImportError, OSError) as exc:
        raise TrustedReleaseError("R145_CANONICAL_API_LOAD_FAILED") from exc
    finally:
        sys.path[:] = original_path
        sys.dont_write_bytecode = original_dont_write
    resolver = getattr(module, "resolve_candidate_domain_authority", None)
    guard = getattr(module, "evaluate_signal_task_route_domain_guard", None)
    if not callable(resolver) or not callable(guard):
        raise TrustedReleaseError("R145_CANONICAL_API_INCOMPLETE")
    return resolver, guard


def _validate_proposal(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TrustedReleaseError("PROPOSAL_NOT_OBJECT")
    proposal = dict(value)
    injected = sorted(set(proposal) & _TRUSTED_CALLER_FIELDS)
    if injected:
        raise TrustedReleaseError(
            "CALLER_TRUSTED_STATE_INJECTION_FORBIDDEN", f"/{injected[0]}"
        )
    missing = sorted(_PROPOSAL_FIELDS - set(proposal))
    if missing:
        raise TrustedReleaseError("PROPOSAL_FIELD_MISSING", f"/{missing[0]}")
    extra = sorted(set(proposal) - _PROPOSAL_FIELDS)
    if extra:
        raise TrustedReleaseError("PROPOSAL_FIELD_UNRECOGNIZED", f"/{extra[0]}")
    if proposal.get("schema_version") != PROPOSAL_SCHEMA:
        raise TrustedReleaseError("PROPOSAL_SCHEMA_INVALID", "/schema_version")
    if not isinstance(proposal.get("signal_primary_domain"), str) or not proposal[
        "signal_primary_domain"
    ].strip():
        raise TrustedReleaseError("SIGNAL_PRIMARY_DOMAIN_INVALID", "/signal_primary_domain")
    return json.loads(_canonical(proposal))


@dataclass(frozen=True)
class _VerifiedR145DomainBinding:
    domain_id: str
    project_id: str
    repository: str
    canonical_commit: str
    writeback_owner: str
    binding_digest: str
    authority_refs: tuple[str, ...]
    legacy_compatibility: bool
    _seal: object = field(repr=False, compare=False)


def _bind_r145_domain_authority(
    root: Path,
    *,
    domain_id: str,
    snapshot: Mapping[str, Any],
    expected_canonical_main: str,
    coordinator_repository: str = COORDINATOR_REPOSITORY,
    exact_read_proofs: Sequence[Any] = (),
    live_observation_proof: Any = None,
) -> _VerifiedR145DomainBinding:
    """Mint one invocation-local capability only from the existing R145 resolver."""
    if not isinstance(domain_id, str) or not domain_id.strip():
        raise TrustedReleaseError("DOMAIN_ID_INVALID")
    resolve_candidate_domain_authority, _ = _load_r145_api(root)
    resolved = resolve_candidate_domain_authority(
        {"proposed_primary_domain": domain_id},
        snapshot,
        expected_canonical_main=expected_canonical_main,
        coordinator_repository=coordinator_repository,
        exact_read_proofs=exact_read_proofs,
        live_observation_proof=live_observation_proof,
    )
    if not resolved.get("valid"):
        raise TrustedReleaseError(
            str(resolved.get("reason") or "R145_DOMAIN_AUTHORITY_UNVERIFIED")
        )
    required = (
        "domain_id",
        "project_id",
        "repository",
        "canonical_commit",
        "writeback_owner",
        "binding_digest",
    )
    if any(
        not isinstance(resolved.get(name), str) or not resolved[name]
        for name in required
    ):
        raise TrustedReleaseError("R145_DOMAIN_AUTHORITY_RESULT_INCOMPLETE")
    if not _SHA40.fullmatch(resolved["canonical_commit"]):
        raise TrustedReleaseError("R145_DOMAIN_CANONICAL_COMMIT_INVALID")
    refs = resolved.get("authority_refs")
    if not isinstance(refs, list) or not refs or not all(
        isinstance(item, str) and item for item in refs
    ):
        raise TrustedReleaseError("R145_DOMAIN_AUTHORITY_REFS_INCOMPLETE")
    return _VerifiedR145DomainBinding(
        domain_id=resolved["domain_id"],
        project_id=resolved["project_id"],
        repository=resolved["repository"],
        canonical_commit=resolved["canonical_commit"],
        writeback_owner=resolved["writeback_owner"],
        binding_digest=resolved["binding_digest"],
        authority_refs=tuple(sorted(refs)),
        legacy_compatibility=resolved.get("legacy_compatibility") is True,
        _seal=_DOMAIN_BINDING_SEAL,
    )


def _require_verified_binding(value: Any) -> _VerifiedR145DomainBinding:
    if not isinstance(value, _VerifiedR145DomainBinding) or value._seal is not _DOMAIN_BINDING_SEAL:
        raise TrustedReleaseError("R145_VERIFIED_DOMAIN_BINDING_REQUIRED")
    return value


def _materialize_active_work_items(
    claims_doc: Mapping[str, Any],
) -> list[dict[str, Any]]:
    claims = claims_doc.get("claims")
    if not isinstance(claims, list):
        raise TrustedReleaseError("CANONICAL_CLAIMS_DOCUMENT_INVALID")
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(claims):
        if not isinstance(raw, Mapping):
            raise TrustedReleaseError("CANONICAL_CLAIM_INVALID", f"/claims/{index}")
        state = str(raw.get("claim_state", ""))
        if state not in _ACTIVE_WORK_STATES:
            continue
        binding = raw.get("route_binding")
        if (
            not isinstance(binding, Mapping)
            or not isinstance(binding.get("task_id"), str)
            or not binding["task_id"]
        ):
            raise TrustedReleaseError(
                "CANONICAL_ACTIVE_CLAIM_ROUTE_BINDING_INVALID",
                f"/claims/{index}/route_binding",
            )
        missing = [field for field in _COLLISION_FIELDS if field not in raw]
        if missing:
            raise TrustedReleaseError(
                "CANONICAL_ACTIVE_CLAIM_SURFACE_INCOMPLETE",
                f"/claims/{index}/{missing[0]}",
            )
        item: dict[str, Any] = {
            "task_id": binding["task_id"],
            "owns_coherent_change_surface": raw.get(
                "owns_coherent_change_surface"
            )
            is True,
        }
        for field_name in _COLLISION_FIELDS:
            field_value = raw[field_name]
            if not isinstance(field_value, list):
                raise TrustedReleaseError(
                    "CANONICAL_ACTIVE_CLAIM_SURFACE_INVALID",
                    f"/claims/{index}/{field_name}",
                )
            item[field_name] = json.loads(_canonical(field_value))
        result.append(item)
    return result


def _trusted_observations(
    root: Path, head: str
) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    paths = (CLAIMS_FILE, GPT_WORKERS_REGISTRY, PROGRAM_CONTROL_TOWER)
    refs = tuple(_exact_path_ref(root, head, path) for path in paths)
    observations = [
        {
            "scope": "second-brain/canonical-checkout",
            "revision": head,
            "evidence_ref": f"git://{COORDINATOR_REPOSITORY}@{head}",
            "status": "CURRENT",
        },
        {
            "scope": "control-tower/work-claims",
            "revision": head,
            "evidence_ref": refs[0],
            "status": "CURRENT",
        },
        {
            "scope": "control-tower/gpt-worker-slots",
            "revision": head,
            "evidence_ref": refs[1],
            "status": "CURRENT",
        },
    ]
    return observations, refs


def evaluate_trusted_release_proposal(
    repo_root: str | Path,
    proposal_value: Mapping[str, Any],
    *,
    expected_coordinator_main: str,
    authority_snapshot: Mapping[str, Any],
    authority_exact_read_proofs: Sequence[Any] = (),
    authority_live_observation_proof: Any = None,
) -> dict[str, Any]:
    """Bind one untrusted proposal to current Control Tower state and fresh R145 authority."""
    root = Path(repo_root).resolve()
    proposal = _validate_proposal(proposal_value)

    if not _SHA40.fullmatch(str(expected_coordinator_main)):
        raise TrustedReleaseError("EXPECTED_CANONICAL_MAIN_INVALID")
    before = _head(root)
    if before != expected_coordinator_main:
        raise TrustedReleaseError("CANONICAL_MAIN_DRIFT")
    if not _worktree_clean(root):
        raise TrustedReleaseError("TRUSTED_REPOSITORY_WORKTREE_DIRTY")

    binding = _bind_r145_domain_authority(
        root,
        domain_id=proposal["signal_primary_domain"],
        snapshot=authority_snapshot,
        expected_canonical_main=expected_coordinator_main,
        exact_read_proofs=authority_exact_read_proofs,
        live_observation_proof=authority_live_observation_proof,
    )
    binding = _require_verified_binding(binding)
    if binding.repository == COORDINATOR_REPOSITORY and binding.canonical_commit != before:
        raise TrustedReleaseError("R145_DOMAIN_BINDING_STALE_FOR_COORDINATOR")

    control_report = scan_repository(root)
    if control_report.get("errors"):
        raise TrustedReleaseError("CONTROL_TOWER_SCAN_FAILED")
    claims_report = validate_claims(root)
    if claims_report.get("errors") or claims_report.get("claim_structural_check") != "PASS":
        raise TrustedReleaseError("WORK_CLAIM_VALIDATION_FAILED")

    claims_doc = load_yaml(root / CLAIMS_FILE)
    active_work = _materialize_active_work_items(claims_doc)
    observations, exact_refs = _trusted_observations(root, before)

    _, evaluate_signal_task_route_domain_guard = _load_r145_api(root)
    domain_guard = evaluate_signal_task_route_domain_guard(
        signal_primary_domain=proposal["signal_primary_domain"],
        task_target_domain=proposal["proposed_target_domain"],
        route_authority_domain=binding.domain_id,
        writeback_owner_domain=binding.domain_id,
    )
    authority_binding = {
        "owner_domain": binding.domain_id,
        "writeback_owner": binding.writeback_owner,
        "compatible": bool(domain_guard.get("eligible_for_normal_release_gates")),
    }

    candidate = dict(proposal)
    candidate.pop("signal_primary_domain")
    candidate["schema_version"] = "TaskReleaseCandidate/v1"
    candidate["observations"] = observations
    candidate["authority_binding"] = authority_binding
    candidate["existing_work_items"] = active_work

    try:
        impact_receipt = evaluate_release_candidate(candidate)
    except ImpactGateError as exc:
        raise TrustedReleaseError(exc.code, exc.path) from exc

    after = _head(root)
    if after != before or not _worktree_clean(root):
        raise TrustedReleaseError("TRUSTED_REPOSITORY_STATE_DRIFT")

    context = {
        "coordinator_repository": COORDINATOR_REPOSITORY,
        "canonical_main": before,
        "exact_refs": list(exact_refs),
        "control_tower_scan_digest": _digest(control_report),
        "work_claim_validation_digest": _digest(claims_report),
        "active_work_digest": _digest(active_work),
        "r145_binding_digest": binding.binding_digest,
        "r145_authority_refs": list(binding.authority_refs),
        "domain_guard": domain_guard,
    }
    wrapper = {
        "schema_version": TRUSTED_RECEIPT_SCHEMA,
        "release_candidate_id": proposal["release_candidate_id"],
        "trusted_context": context,
        "impact_receipt": impact_receipt,
        "authority_boundary": {
            "evidence_only": True,
            "creates_task": False,
            "creates_route": False,
            "creates_work_claim": False,
            "creates_worker_slot": False,
            "grants_execution_authority": False,
            "grants_domain_write": False,
            "grants_signal_write": False,
            "grants_w3_write": False,
            "grants_merge_authority": False,
        },
    }
    wrapper["receipt_digest"] = _digest(wrapper)
    return wrapper
