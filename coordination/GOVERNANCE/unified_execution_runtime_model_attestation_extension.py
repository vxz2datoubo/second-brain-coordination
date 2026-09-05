"""Fresh runtime-model classification attestation for governed Codex process starts.

This extension does not classify model names itself. It requires a task-bound attestation
that is freshly re-read from canonical main through the existing protected transport.
The attestation binds the runtime-resolved model, invocation mode and runtime compute class
to the exact dispatch and compute authorization before process start.
"""
from dataclasses import dataclass

_RUNTIME_MODEL_ATTESTATION_ISSUER = object()

_RUNTIME_ATTESTATION_FIELDS = (
    "attestation_status",
    "resolved_model_display_name",
    "model_resolution_status",
    "runtime_compute_class",
    "runtime_invocation_mode",
    "classifier_provenance",
    "dispatch_compute_lane_receipt_digest",
    "compute_authorization_ref",
    "compute_authorization_receipt_digest",
)


@dataclass(frozen=True)
class VerifiedRuntimeModelClassificationAttestation:
    _payload: Mapping[str, Any]
    _issuer: object

    def as_mapping(self) -> Mapping[str, Any]:
        if self._issuer is not _RUNTIME_MODEL_ATTESTATION_ISSUER:
            raise ExecutionContractError("runtime_model_attestation: untrusted issuer")
        return self._payload


def _issue_runtime_model_attestation(
    payload: Mapping[str, Any],
) -> VerifiedRuntimeModelClassificationAttestation:
    return VerifiedRuntimeModelClassificationAttestation(
        base._freeze(payload), _RUNTIME_MODEL_ATTESTATION_ISSUER
    )


def _runtime_model_attestation_mapping(snapshot: Any) -> Mapping[str, Any]:
    if not isinstance(snapshot, VerifiedRuntimeModelClassificationAttestation):
        raise ExecutionContractError(
            "runtime_model_attestation: caller-supplied mapping is not trusted attestation"
        )
    return snapshot.as_mapping()


def _reject_duplicate_runtime_attestation_keys(text: str) -> None:
    protected = {
        *base.COMMON_IDENTITY_FIELDS,
        *_RUNTIME_ATTESTATION_FIELDS,
    }
    counts: dict[str, int] = {}
    for line in text.splitlines():
        if not line or line.startswith((" ", "\t")) or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_]+):", line)
        if match and match.group(1) in protected:
            key = match.group(1)
            counts[key] = counts.get(key, 0) + 1
    duplicates = sorted(key for key, count in counts.items() if count > 1)
    if duplicates:
        raise ExecutionContractError(
            "runtime_model_attestation: duplicate protected YAML keys: "
            + ", ".join(duplicates)
        )


def _secure_build_verified_runtime_model_attestation(
    repo_path: str | Path,
    attestation_ref: str,
) -> VerifiedRuntimeModelClassificationAttestation:
    """Fresh-read a task-bound runtime classification attestation from canonical main."""
    base._validate_ref(attestation_ref)
    canonical_main_sha, read = _protected_open(repo_path)
    raw = read(attestation_ref)
    text = raw.decode("utf-8")
    _reject_duplicate_runtime_attestation_keys(text)

    required = (*base.COMMON_IDENTITY_FIELDS, *_RUNTIME_ATTESTATION_FIELDS)
    payload: dict[str, Any] = {key: base._scalar(text, key) for key in required}

    if payload["control_plane_repository"] != base.TRUSTED_CONTROL_PLANE_REPOSITORY:
        raise ExecutionContractError(
            "runtime_model_attestation: wrong control-plane repository"
        )
    if payload["attestation_status"] != "ATTESTED":
        raise ExecutionContractError(
            "runtime_model_attestation: status is not ATTESTED"
        )
    if payload["model_resolution_status"] != "RESOLVED":
        raise ExecutionContractError(
            "runtime_model_attestation: runtime model is not RESOLVED"
        )
    if not str(payload["resolved_model_display_name"]).strip():
        raise ExecutionContractError(
            "runtime_model_attestation: resolved runtime model identity is empty"
        )
    if payload["runtime_compute_class"] not in {"STANDARD", "FRONTIER"}:
        raise ExecutionContractError(
            "runtime_model_attestation: runtime compute class is not classified"
        )
    if not str(payload["runtime_invocation_mode"]).strip():
        raise ExecutionContractError(
            "runtime_model_attestation: invocation mode is empty"
        )
    if not str(payload["classifier_provenance"]).strip():
        raise ExecutionContractError(
            "runtime_model_attestation: classifier provenance is empty"
        )
    for field in (
        "dispatch_compute_lane_receipt_digest",
        "compute_authorization_ref",
        "compute_authorization_receipt_digest",
    ):
        if not str(payload[field]).strip():
            raise ExecutionContractError(
                f"runtime_model_attestation: {field} is empty"
            )

    payload["canonical_main_sha"] = canonical_main_sha
    payload["attestation_ref"] = attestation_ref
    payload["attestation_document_digest"] = base._sha(raw)
    payload["runtime_model_attestation_receipt_digest"] = base._json_digest(payload)
    return _issue_runtime_model_attestation(payload)


def _fresh_runtime_model_attestation(
    repo_path: str | Path,
    attestation_ref: str,
) -> VerifiedRuntimeModelClassificationAttestation:
    fresh = _secure_build_verified_runtime_model_attestation(repo_path, attestation_ref)
    mapping = _runtime_model_attestation_mapping(fresh)
    _terminal_remote_main_recheck(repo_path, str(mapping["canonical_main_sha"]))
    return fresh


def validate_runtime_model_attestation(
    repo_path: str | Path,
    attestation_ref: str,
    claimed_snapshot: VerifiedRuntimeModelClassificationAttestation,
) -> VerifiedRuntimeModelClassificationAttestation:
    claimed = _runtime_model_attestation_mapping(claimed_snapshot)
    fresh = _fresh_runtime_model_attestation(repo_path, attestation_ref)
    canonical = _runtime_model_attestation_mapping(fresh)
    if not _same_snapshot(claimed, canonical):
        raise ExecutionContractError(
            "runtime_model_attestation: claimed attestation differs from fresh canonical state"
        )
    return fresh


def _validate_runtime_model_binding(
    attestation: VerifiedRuntimeModelClassificationAttestation,
    admission: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    fresh_authority: base.VerifiedCanonicalAuthority,
) -> None:
    runtime = _runtime_model_attestation_mapping(attestation)
    authority = _authority_mapping(fresh_authority)

    base._same_identity(runtime, dispatch, "runtime_model_attestation.dispatch")
    base._same_identity(runtime, authority, "runtime_model_attestation.authority")
    if runtime["canonical_main_sha"] != authority["canonical_main_sha"]:
        raise ExecutionContractError(
            "runtime_model_attestation: attestation and writer authority are from different main states"
        )

    for mapping, label in ((dispatch, "dispatch"), (admission, "local_admission")):
        base._require(
            mapping,
            (
                "runtime_invocation_mode",
                "runtime_model_attestation_ref",
                "runtime_model_attestation_receipt_digest",
            ),
            f"{label}.runtime_model_attestation",
        )

    if runtime["resolved_model_display_name"] != dispatch["resolved_model_display_name"]:
        raise ExecutionContractError(
            "runtime_model_attestation: resolved model does not match dispatch"
        )
    if runtime["model_resolution_status"] != dispatch["model_resolution_status"]:
        raise ExecutionContractError(
            "runtime_model_attestation: model resolution status does not match dispatch"
        )
    if runtime["runtime_compute_class"] != dispatch["compute_class"]:
        raise ExecutionContractError(
            "runtime_model_attestation: runtime compute class does not match authorized dispatch class"
        )
    if runtime["runtime_invocation_mode"] != dispatch["runtime_invocation_mode"]:
        raise ExecutionContractError(
            "runtime_model_attestation: invocation mode does not match dispatch"
        )
    if runtime["dispatch_compute_lane_receipt_digest"] != dispatch["compute_lane_receipt_digest"]:
        raise ExecutionContractError(
            "runtime_model_attestation: dispatch receipt binding mismatch"
        )
    if runtime["compute_authorization_ref"] != dispatch.get("compute_authorization_ref"):
        raise ExecutionContractError(
            "runtime_model_attestation: compute authorization ref mismatch"
        )
    if runtime["compute_authorization_receipt_digest"] != dispatch.get(
        "compute_authorization_receipt_digest"
    ):
        raise ExecutionContractError(
            "runtime_model_attestation: compute authorization receipt mismatch"
        )
    if dispatch["runtime_model_attestation_ref"] != runtime["attestation_ref"]:
        raise ExecutionContractError(
            "runtime_model_attestation: dispatch attestation ref mismatch"
        )
    if dispatch["runtime_model_attestation_receipt_digest"] != runtime[
        "runtime_model_attestation_receipt_digest"
    ]:
        raise ExecutionContractError(
            "runtime_model_attestation: dispatch attestation receipt mismatch"
        )

    for field in (
        "runtime_invocation_mode",
        "runtime_model_attestation_ref",
        "runtime_model_attestation_receipt_digest",
    ):
        if admission[field] != dispatch[field]:
            raise ExecutionContractError(
                f"runtime_model_attestation: local admission {field} does not match dispatch"
            )


_pre_runtime_attestation_validate_process_start = validate_process_start


def validate_process_start(
    repo_path: str | Path,
    admission: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    claimed_snapshot: base.VerifiedCanonicalAuthority,
    compute_authorization_ref: str | None = None,
    claimed_compute_authorization: base.VerifiedComputeLaneAuthorization | None = None,
    runtime_model_attestation_ref: str | None = None,
    claimed_runtime_model_attestation: VerifiedRuntimeModelClassificationAttestation | None = None,
) -> base.VerifiedCanonicalAuthority:
    """Validate writer/compute authority and actual runtime classification before launch."""
    fresh_authority = _pre_runtime_attestation_validate_process_start(
        repo_path,
        admission,
        dispatch,
        claimed_snapshot,
        compute_authorization_ref,
        claimed_compute_authorization,
    )

    carrier = dispatch.get("carrier")
    if carrier not in base._CODEX_CARRIERS:
        if runtime_model_attestation_ref is not None or claimed_runtime_model_attestation is not None:
            raise ExecutionContractError(
                "runtime_model_attestation: non-Codex process cannot consume Codex runtime attestation"
            )
        return fresh_authority

    if not runtime_model_attestation_ref or claimed_runtime_model_attestation is None:
        raise ExecutionContractError(
            "runtime_model_attestation: Codex process-start requires fresh trusted runtime classification"
        )

    fresh_runtime = validate_runtime_model_attestation(
        repo_path,
        runtime_model_attestation_ref,
        claimed_runtime_model_attestation,
    )
    _validate_runtime_model_binding(
        fresh_runtime,
        admission,
        dispatch,
        fresh_authority,
    )
    return fresh_authority
