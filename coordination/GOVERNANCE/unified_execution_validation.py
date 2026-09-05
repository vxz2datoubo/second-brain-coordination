"""Dependency-free trust-boundary validators for the unified execution fabric."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

TRUSTED_CONTROL_PLANE_REPOSITORY = "vxz2datoubo/second-brain-coordination"
TRUSTED_CONTROL_PLANE_URL = "https://github.com/vxz2datoubo/second-brain-coordination.git"
ACTIVE_TASK_INDEX_REF = "coordination/ACTIVE-WORKBUDDY-TASK.yaml"
PROJECT_ADAPTER_PATHS = (
    "coordination/EXECUTION/PROJECT-ADAPTERS/SECOND-BRAIN.yaml",
    "coordination/EXECUTION/PROJECT-ADAPTERS/TRADING-SYSTEM.yaml",
    "coordination/EXECUTION/PROJECT-ADAPTERS/REALTIME-INTERACTIVE-FILM.yaml",
    "coordination/EXECUTION/PROJECT-ADAPTERS/AI-DIRECTOR.yaml",
)


class ExecutionContractError(ValueError):
    """Raised when an execution contract fails closed."""


COMMON_IDENTITY_FIELDS = (
    "control_plane_repository",
    "execution_repository",
    "project_id",
    "task_id",
    "route_epoch",
    "exact_base_sha",
    "implementation_branch",
    "collision_domain",
)
AUTHORITY_REF_FIELDS = (
    "active_task_index_ref",
    "canonical_route_ref",
    "work_claim_ref",
    "task_lease_ref",
    "executor_reservation_ref",
    "prewrite_snapshot_ref",
    "executable_batch_ref",
)
GLOBAL_CARRIERS = {
    "GPT_DIRECT",
    "WORKBUDDY_CLI_HEADLESS",
    "WORKBUDDY_CLI_WEBUI",
    "WORKBUDDY_DESKTOP_INTERACTIVE",
    "CODEX_FRONTIER_ESCALATION",
}
NON_WEAKENABLE_INVARIANTS = {
    "single_writer_per_collision_domain",
    "exact_head_review_identity",
    "no_self_review",
    "no_self_merge",
    "credential_secret_exclusion",
    "active_task_authority_required",
}
PROJECT_ADAPTER_REQUIRED_FIELDS = (
    "project_id",
    "global_protocol_id",
    "inherits_global_invariants",
    "control_plane_repository",
    "execution_repository",
    "repositories",
    "canonical_entrypoints",
    "authority",
    "allowed_execution_carriers",
    "default_model_profiles",
    "collision_domains",
    "tool_interfaces",
    "hard_boundaries",
    "acceptance",
    "handoff",
)

_ISSUER = object()


@dataclass(frozen=True)
class VerifiedCanonicalAuthority:
    _payload: Mapping[str, Any]
    _issuer: object

    def as_mapping(self) -> Mapping[str, Any]:
        if self._issuer is not _ISSUER:
            raise ExecutionContractError("canonical_authority: untrusted issuer")
        return self._payload


@dataclass(frozen=True)
class VerifiedReleaseWitness:
    _payload: Mapping[str, Any]
    _issuer: object

    def as_mapping(self) -> Mapping[str, Any]:
        if self._issuer is not _ISSUER:
            raise ExecutionContractError("release_witness: untrusted issuer")
        return self._payload


def _freeze(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    def convert(value: Any) -> Any:
        if isinstance(value, Mapping):
            return MappingProxyType({k: convert(v) for k, v in value.items()})
        if isinstance(value, list):
            return tuple(convert(v) for v in value)
        return value

    return MappingProxyType({k: convert(v) for k, v in mapping.items()})


def _issue_authority(payload: Mapping[str, Any]) -> VerifiedCanonicalAuthority:
    return VerifiedCanonicalAuthority(_freeze(payload), _ISSUER)


def _issue_release(payload: Mapping[str, Any]) -> VerifiedReleaseWitness:
    return VerifiedReleaseWitness(_freeze(payload), _ISSUER)


def _require(mapping: Mapping[str, Any], fields: Sequence[str], label: str) -> None:
    missing = [field for field in fields if field not in mapping or mapping[field] in (None, "")]
    if missing:
        raise ExecutionContractError(f"{label}: missing required fields: {', '.join(missing)}")


def _same_identity(left: Mapping[str, Any], right: Mapping[str, Any], label: str) -> None:
    _require(left, COMMON_IDENTITY_FIELDS, f"{label}.left")
    _require(right, COMMON_IDENTITY_FIELDS, f"{label}.right")
    mismatched = [field for field in COMMON_IDENTITY_FIELDS if left[field] != right[field]]
    if mismatched:
        raise ExecutionContractError(f"{label}: identity mismatch: {', '.join(mismatched)}")


def _sha(data: bytes) -> str:
    return "sha256:" + sha256(data).hexdigest()


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    return value


def _json_digest(value: Any) -> str:
    encoded = json.dumps(
        _json_ready(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return _sha(encoded)


def _scalar(text: str, key: str, *, required: bool = True) -> Any:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.*?)\s*$", text)
    if not match:
        if required:
            raise ExecutionContractError(f"yaml: missing top-level scalar {key}")
        return None
    raw = match.group(1).strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw in {"true", "false"}:
        return raw == "true"
    if raw in {"null", "~"}:
        return None
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return raw


def _nested_scalar(text: str, section: str, key: str, *, required: bool = True) -> Any:
    block = _section(text, section, required=required)
    if block is None:
        return None
    match = re.search(rf"(?m)^\s+{re.escape(key)}:\s*(.*?)\s*$", block)
    if not match:
        if required:
            raise ExecutionContractError(f"yaml: missing {section}.{key}")
        return None
    raw = match.group(1).strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw in {"true", "false"}:
        return raw == "true"
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return raw


def _section(text: str, key: str, *, required: bool = True) -> str | None:
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if re.fullmatch(rf"{re.escape(key)}:\s*", line):
            start = idx + 1
            break
    if start is None:
        if required:
            raise ExecutionContractError(f"yaml: missing section {key}")
        return None
    end = len(lines)
    for idx in range(start, len(lines)):
        line = lines[idx]
        if line and not line.startswith((" ", "\t", "#")) and re.match(
            r"^[A-Za-z0-9_].*:\s*", line
        ):
            end = idx
            break
    return "\n".join(lines[start:end])


def _list(text: str, key: str, *, required: bool = True) -> list[str]:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        match = re.fullmatch(rf"(\s*){re.escape(key)}:\s*", line)
        if not match:
            continue
        indent = len(match.group(1))
        values: list[str] = []
        for item in lines[idx + 1 :]:
            if not item.strip():
                continue
            current = len(item) - len(item.lstrip(" "))
            if current <= indent:
                break
            if current == indent + 2 and item.lstrip().startswith("- "):
                raw = item.lstrip()[2:].strip()
                if ":" in raw and not (raw.startswith('"') and raw.endswith('"')):
                    continue
                if raw.startswith('"') and raw.endswith('"'):
                    raw = raw[1:-1]
                values.append(raw)
        if required and not values:
            raise ExecutionContractError(f"yaml: empty list {key}")
        return values
    if required:
        raise ExecutionContractError(f"yaml: missing list {key}")
    return []


def _validate_ref(path: str) -> None:
    parsed = Path(path)
    if parsed.is_absolute() or ".." in parsed.parts or not path.startswith("coordination/"):
        raise ExecutionContractError(f"authority: unsafe repository path {path}")


def _run_git(repo_path: str | Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ExecutionContractError(
            f"trusted git readback failed: {' '.join(args)}: {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def _open_trusted_main(repo_path: str | Path) -> tuple[str, Callable[[str], bytes]]:
    remote = _run_git(repo_path, "ls-remote", TRUSTED_CONTROL_PLANE_URL, "refs/heads/main")
    fields = remote.split()
    if len(fields) < 2 or not re.fullmatch(r"[0-9a-f]{40}", fields[0]):
        raise ExecutionContractError("trusted git readback: invalid main identity")
    observed = fields[0]
    _run_git(
        repo_path,
        "fetch",
        "--quiet",
        "--no-tags",
        TRUSTED_CONTROL_PLANE_URL,
        "refs/heads/main",
    )
    fetched = _run_git(repo_path, "rev-parse", "FETCH_HEAD")
    if fetched != observed:
        raise ExecutionContractError("trusted git readback: main moved during readback")

    def read(path: str) -> bytes:
        _validate_ref(path)
        proc = subprocess.run(
            ["git", "-C", str(repo_path), "show", f"{observed}:{path}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode != 0:
            raise ExecutionContractError(f"trusted git readback: cannot read {path}")
        return proc.stdout

    return observed, read


def _resolve_project(read: Callable[[str], bytes], canonical_project_key: str) -> tuple[str, str]:
    matches: list[tuple[str, str]] = []
    for path in PROJECT_ADAPTER_PATHS:
        text = read(path).decode("utf-8")
        aliases = _list(text, "authority_project_aliases", required=False)
        project_id = _scalar(text, "project_id")
        if canonical_project_key == project_id or canonical_project_key in aliases:
            matches.append((project_id, _scalar(text, "execution_repository")))
    if len(matches) != 1:
        raise ExecutionContractError(
            "canonical_authority: project alias did not resolve uniquely"
        )
    return matches[0]


def build_verified_canonical_authority(repo_path: str | Path) -> VerifiedCanonicalAuthority:
    """Fresh-read canonical main and issue a non-caller-constructible authority object."""
    canonical_main_sha, read = _open_trusted_main(repo_path)
    active_raw = read(ACTIVE_TASK_INDEX_REF)
    active = active_raw.decode("utf-8")
    refs = {
        "active_task_index_ref": ACTIVE_TASK_INDEX_REF,
        "canonical_route_ref": _scalar(active, "canonical_route"),
        "work_claim_ref": _scalar(active, "work_claim"),
        "task_lease_ref": _scalar(active, "task_lease"),
        "executor_reservation_ref": _scalar(active, "executor_reservation"),
        "prewrite_snapshot_ref": _scalar(active, "prewrite_snapshot"),
        "executable_batch_ref": _scalar(active, "executable_batch"),
    }
    for path in refs.values():
        _validate_ref(path)
    raw_docs = {name: read(path) for name, path in refs.items()}
    digests = {name: _sha(data) for name, data in raw_docs.items()}

    route = raw_docs["canonical_route_ref"].decode("utf-8")
    lease = raw_docs["task_lease_ref"].decode("utf-8")
    task_id = _scalar(active, "task_id")
    route_epoch = _scalar(active, "route_epoch")
    branch = _scalar(active, "implementation_branch")
    exact_base_sha = _nested_scalar(active, "source_checkpoint", "exact_head")
    canonical_project_key = _scalar(route, "project")
    project_id, execution_repository = _resolve_project(read, canonical_project_key)

    for label, document in (("route", route), ("lease", lease)):
        if _scalar(document, "task_id") != task_id:
            raise ExecutionContractError(f"canonical_authority: {label} task mismatch")
        if _scalar(document, "route_epoch") != route_epoch:
            raise ExecutionContractError(f"canonical_authority: {label} epoch mismatch")
    if _scalar(active, "status") != "READY" or _scalar(route, "status") != "READY":
        raise ExecutionContractError("canonical_authority: route is not READY")
    if _scalar(active, "execution_allowed") is not True or _scalar(
        route, "execution_allowed"
    ) is not True:
        raise ExecutionContractError("canonical_authority: execution is not allowed")
    if _scalar(lease, "lease_state") != "ACTIVE" or _scalar(
        lease, "execution_allowed"
    ) is not True:
        raise ExecutionContractError("canonical_authority: lease is not ACTIVE")
    if _scalar(lease, "implementation_branch") != branch:
        raise ExecutionContractError("canonical_authority: lease branch mismatch")

    active_paths = _list(active, "authorized_paths")
    lease_paths = _list(lease, "exclusive_write_surface")
    route_paths = _list(route, "workbuddy_exclusive")
    if set(active_paths) != set(lease_paths) or set(active_paths) != set(route_paths):
        raise ExecutionContractError("canonical_authority: write surfaces disagree")
    collision_domain = "WRITESET_SHA256:" + sha256(
        json.dumps(sorted(active_paths), separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    denials = sorted(
        set(
            _list(active, "hard_boundaries")
            + ["NO_DIRECT_MAIN_WRITE", "NO_SELF_REVIEW", "NO_SELF_MERGE"]
        )
    )
    grants = ["EXECUTE_TASK"]
    if active_paths:
        grants.append("WRITE_AUTHORIZED_PATHS")

    payload: dict[str, Any] = {
        "control_plane_repository": TRUSTED_CONTROL_PLANE_REPOSITORY,
        "execution_repository": execution_repository,
        "project_id": project_id,
        "task_id": task_id,
        "route_epoch": route_epoch,
        "exact_base_sha": exact_base_sha,
        "implementation_branch": branch,
        "collision_domain": collision_domain,
        "canonical_main_sha": canonical_main_sha,
        "authority_refs": refs,
        "authority_digests": digests,
        "route_status": "READY",
        "execution_allowed": True,
        "lease_released": False,
        "lease_replaced": False,
        "authority_replaced": False,
        "fresh_readback": True,
        "authorized_paths": active_paths,
        "authority_grants": grants,
        "authority_denials": denials,
    }
    receipt_material = {
        key: payload[key]
        for key in (
            *COMMON_IDENTITY_FIELDS,
            "canonical_main_sha",
            "authority_refs",
            "authority_digests",
            "route_status",
            "execution_allowed",
            "authorized_paths",
            "authority_grants",
            "authority_denials",
        )
    }
    payload["authority_chain_receipt_digest"] = _json_digest(receipt_material)
    return _issue_authority(payload)


def build_verified_release_witness(
    repo_path: str | Path, release_ref: str
) -> VerifiedReleaseWitness:
    """Fresh-read a canonical release document and recompute its release receipt."""
    _validate_ref(release_ref)
    canonical_main_sha, read = _open_trusted_main(repo_path)
    raw = read(release_ref)
    text = raw.decode("utf-8")
    required = (
        "control_plane_repository",
        "execution_repository",
        "project_id",
        "task_id",
        "route_epoch",
        "exact_base_sha",
        "implementation_branch",
        "collision_domain",
        "writer_lease_ref",
        "released_lease_digest",
        "writer_lease_id",
        "writer_lease_generation",
        "release_status",
    )
    payload = {key: _scalar(text, key) for key in required}
    if payload["control_plane_repository"] != TRUSTED_CONTROL_PLANE_REPOSITORY:
        raise ExecutionContractError("release_witness: wrong control-plane repository")
    if payload["release_status"] != "RELEASED":
        raise ExecutionContractError("release_witness: release document is not RELEASED")
    _validate_ref(payload["writer_lease_ref"])
    payload["canonical_main_sha"] = canonical_main_sha
    payload["release_ref"] = release_ref
    payload["release_document_digest"] = _sha(raw)
    payload["release_receipt_digest"] = _json_digest(payload)
    return _issue_release(payload)


def _authority_mapping(
    authority: VerifiedCanonicalAuthority,
) -> Mapping[str, Any]:
    if not isinstance(authority, VerifiedCanonicalAuthority):
        raise ExecutionContractError(
            "canonical_authority: caller-supplied mapping is not trusted authority"
        )
    return authority.as_mapping()


def _release_mapping(witness: VerifiedReleaseWitness) -> Mapping[str, Any]:
    if not isinstance(witness, VerifiedReleaseWitness):
        raise ExecutionContractError(
            "release_witness: caller-supplied mapping is not trusted release evidence"
        )
    return witness.as_mapping()


def validate_canonical_authority(authority: VerifiedCanonicalAuthority) -> None:
    mapping = _authority_mapping(authority)
    _require(
        mapping,
        COMMON_IDENTITY_FIELDS
        + (
            "canonical_main_sha",
            "authority_chain_receipt_digest",
            "authority_refs",
            "authority_digests",
            "route_status",
            "execution_allowed",
            "fresh_readback",
            "authorized_paths",
            "authority_grants",
            "authority_denials",
        ),
        "canonical_authority",
    )
    material = {
        key: mapping[key]
        for key in (
            *COMMON_IDENTITY_FIELDS,
            "canonical_main_sha",
            "authority_refs",
            "authority_digests",
            "route_status",
            "execution_allowed",
            "authorized_paths",
            "authority_grants",
            "authority_denials",
        )
    }
    if mapping["authority_chain_receipt_digest"] != _json_digest(material):
        raise ExecutionContractError("canonical_authority: receipt recomputation failed")
    if (
        mapping["route_status"] != "READY"
        or mapping["execution_allowed"] is not True
        or mapping["fresh_readback"] is not True
    ):
        raise ExecutionContractError("canonical_authority: inactive or stale")
    _require(
        mapping["authority_refs"], AUTHORITY_REF_FIELDS, "canonical_authority.authority_refs"
    )
    _require(
        mapping["authority_digests"],
        AUTHORITY_REF_FIELDS,
        "canonical_authority.authority_digests",
    )


def validate_dispatch(
    dispatch: Mapping[str, Any], canonical_authority: VerifiedCanonicalAuthority
) -> None:
    validate_canonical_authority(canonical_authority)
    canonical = _authority_mapping(canonical_authority)
    _require(
        dispatch,
        COMMON_IDENTITY_FIELDS
        + (
            "canonical_main_sha",
            "authority_chain_receipt_digest",
            "authority_refs",
            "authority_digests",
            "authorized_paths",
            "authority_grants",
            "authority_denials",
        ),
        "dispatch",
    )
    _same_identity(dispatch, canonical, "dispatch")
    for field in (
        "canonical_main_sha",
        "authority_chain_receipt_digest",
        "authority_refs",
        "authority_digests",
    ):
        if dispatch[field] != canonical[field]:
            raise ExecutionContractError(f"dispatch: {field} mismatch")
    if not set(dispatch["authorized_paths"]) <= set(canonical["authorized_paths"]):
        raise ExecutionContractError("dispatch: authorized paths exceed canonical authority")
    if not set(dispatch["authority_grants"]) <= set(canonical["authority_grants"]):
        raise ExecutionContractError("dispatch: authority grants exceed canonical authority")
    if not set(canonical["authority_denials"]) <= set(dispatch["authority_denials"]):
        raise ExecutionContractError("dispatch: canonical denials were weakened")


def validate_local_admission(
    admission: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    canonical_authority: VerifiedCanonicalAuthority,
) -> None:
    validate_dispatch(dispatch, canonical_authority)
    canonical = _authority_mapping(canonical_authority)
    _require(
        admission,
        COMMON_IDENTITY_FIELDS
        + (
            "canonical_main_sha",
            "route_status",
            "execution_allowed",
            "authority_chain_receipt_digest",
            "authority_refs",
            "authority_digests",
            "authorized_paths",
            "authority_grants",
            "authority_denials",
            "writer_lease_id",
            "writer_lease_generation",
        ),
        "local_admission",
    )
    _same_identity(admission, dispatch, "local_admission.dispatch")
    _same_identity(admission, canonical, "local_admission.canonical")
    if admission["route_status"] != "READY" or admission["execution_allowed"] is not True:
        raise ExecutionContractError("local_admission: route not executable")
    for field in (
        "canonical_main_sha",
        "authority_chain_receipt_digest",
        "authority_refs",
        "authority_digests",
        "authorized_paths",
        "authority_grants",
        "authority_denials",
    ):
        if admission[field] != dispatch[field]:
            raise ExecutionContractError(
                f"local_admission: {field} does not match dispatch"
            )


def validate_carrier_handoff(
    handoff: Mapping[str, Any],
    old_dispatch: Mapping[str, Any],
    old_authority: VerifiedCanonicalAuthority,
    release_witness: VerifiedReleaseWitness,
    new_dispatch: Mapping[str, Any],
    new_admission: Mapping[str, Any],
    new_authority: VerifiedCanonicalAuthority,
) -> None:
    validate_dispatch(old_dispatch, old_authority)
    validate_local_admission(new_admission, new_dispatch, new_authority)
    old = _authority_mapping(old_authority)
    new = _authority_mapping(new_authority)
    release = _release_mapping(release_witness)
    _require(
        handoff,
        COMMON_IDENTITY_FIELDS
        + (
            "from_carrier",
            "to_carrier",
            "checkpoint_head_sha",
            "old_writer_lease_id",
            "old_writer_lease_generation",
            "new_writer_admission_required",
        ),
        "carrier_handoff",
    )
    _same_identity(handoff, old_dispatch, "carrier_handoff.old_dispatch")
    if handoff["new_writer_admission_required"] is not True:
        raise ExecutionContractError(
            "carrier_handoff: new writer admission must be required"
        )
    for field in COMMON_IDENTITY_FIELDS:
        if release[field] != handoff[field]:
            raise ExecutionContractError(
                f"carrier_handoff: release identity mismatch: {field}"
            )
    if (
        release["writer_lease_id"] != handoff["old_writer_lease_id"]
        or release["writer_lease_generation"] != handoff["old_writer_lease_generation"]
    ):
        raise ExecutionContractError("carrier_handoff: old lease identity mismatch")
    if release["writer_lease_ref"] != old["authority_refs"]["task_lease_ref"]:
        raise ExecutionContractError(
            "carrier_handoff: released lease ref does not match old canonical authority"
        )
    if release["released_lease_digest"] != old["authority_digests"]["task_lease_ref"]:
        raise ExecutionContractError(
            "carrier_handoff: released lease digest does not match old canonical authority"
        )
    if release["canonical_main_sha"] != new["canonical_main_sha"]:
        raise ExecutionContractError(
            "carrier_handoff: release witness is not from new admission main"
        )
    _same_identity(new_dispatch, old_dispatch, "carrier_handoff.new_dispatch")
    if (
        new["authority_digests"]["task_lease_ref"]
        == old["authority_digests"]["task_lease_ref"]
    ):
        raise ExecutionContractError(
            "carrier_handoff: new writer reused old lease document"
        )
    if new_admission["writer_lease_id"] == handoff["old_writer_lease_id"]:
        raise ExecutionContractError("carrier_handoff: old writer lease replayed")


def validate_project_adapter(
    adapter: Mapping[str, Any], global_policy: Mapping[str, Any]
) -> None:
    _require(adapter, PROJECT_ADAPTER_REQUIRED_FIELDS, "project_adapter")
    _require(
        global_policy,
        ("protocol_id", "allowed_execution_carriers", "non_weakenable_invariants"),
        "global_policy",
    )
    if adapter["global_protocol_id"] != global_policy["protocol_id"]:
        raise ExecutionContractError("project_adapter: wrong global protocol")
    if adapter["inherits_global_invariants"] is not True:
        raise ExecutionContractError(
            "project_adapter: global invariants must be inherited"
        )
    if not set(adapter["allowed_execution_carriers"]) <= set(
        global_policy["allowed_execution_carriers"]
    ):
        raise ExecutionContractError("project_adapter: carrier set exceeds global policy")
    for field in (
        "repositories",
        "canonical_entrypoints",
        "authority",
        "default_model_profiles",
        "collision_domains",
        "tool_interfaces",
        "hard_boundaries",
        "acceptance",
        "handoff",
    ):
        if not adapter[field]:
            raise ExecutionContractError(
                f"project_adapter: empty required semantic section: {field}"
            )
    overrides = adapter.get("global_invariant_overrides", {})
    for invariant in set(global_policy["non_weakenable_invariants"]) | NON_WEAKENABLE_INVARIANTS:
        if invariant in overrides and overrides[invariant] is not True:
            raise ExecutionContractError(
                f"project_adapter: invariant weakened: {invariant}"
            )
    serialized = json.dumps(_json_ready(adapter), sort_keys=True).lower()
    for forbidden in (
        "unbounded_shell",
        '"merge_authority": true',
        '"review_authority": true',
        '"direct_main_write": true',
        '"place_order_allowed": true',
    ):
        if forbidden in serialized:
            raise ExecutionContractError(
                f"project_adapter: forbidden authority widening: {forbidden}"
            )
    if "global_router" in adapter or "global_task_router" in adapter:
        raise ExecutionContractError("project_adapter: second global router is forbidden")


def parse_and_validate_project_adapter(
    text: str, global_policy: Mapping[str, Any]
) -> Mapping[str, Any]:
    """Parse and validate the real governed adapter semantic surface without PyYAML."""
    top_keys = set(re.findall(r"(?m)^([A-Za-z0-9_]+):", text))
    missing = [key for key in PROJECT_ADAPTER_REQUIRED_FIELDS if key not in top_keys]
    if missing:
        raise ExecutionContractError(
            f"project_adapter_document: missing sections: {', '.join(missing)}"
        )
    adapter: dict[str, Any] = {
        "project_id": _scalar(text, "project_id"),
        "global_protocol_id": _scalar(text, "global_protocol_id"),
        "inherits_global_invariants": _scalar(text, "inherits_global_invariants"),
        "control_plane_repository": _scalar(text, "control_plane_repository"),
        "execution_repository": _scalar(text, "execution_repository"),
        "repositories": _section(text, "repositories"),
        "canonical_entrypoints": _list(text, "canonical_entrypoints"),
        "authority": _section(text, "authority"),
        "allowed_execution_carriers": _list(text, "allowed_execution_carriers"),
        "default_model_profiles": _section(text, "default_model_profiles"),
        "collision_domains": _list(text, "collision_domains"),
        "tool_interfaces": _section(text, "tool_interfaces"),
        "hard_boundaries": _list(text, "hard_boundaries"),
        "acceptance": _section(text, "acceptance"),
        "handoff": _section(text, "handoff"),
    }
    validate_project_adapter(adapter, global_policy)
    lowered = text.lower()
    for forbidden in (
        "merge_authority: true",
        "review_authority: true",
        "direct_main_write: true",
        "place_order_allowed: true",
    ):
        if forbidden in lowered:
            raise ExecutionContractError(
                f"project_adapter_document: forbidden authority widening: {forbidden}"
            )
    return MappingProxyType(adapter)
