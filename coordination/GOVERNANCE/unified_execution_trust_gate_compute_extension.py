"""Fresh process-start compute-lane authorization layered over the canonical trust gate."""
from pathlib import Path as _BootstrapPath

_base_path = _BootstrapPath(__file__).with_name("unified_execution_trust_gate_base.py")
exec(compile(_base_path.read_text(encoding="utf-8"), str(_base_path), "exec"), globals(), globals())
del _base_path, _BootstrapPath


def _compute_mapping(snapshot: Any) -> Mapping[str, Any]:
    if not isinstance(snapshot, base.VerifiedComputeLaneAuthorization):
        raise ExecutionContractError(
            "fresh_trust_gate: claimed compute lane must use the governed snapshot shape"
        )
    return snapshot.as_mapping()


def _reject_duplicate_compute_yaml_keys(text: str) -> None:
    protected = {
        *base.COMMON_IDENTITY_FIELDS,
        "authorization_status",
        "executor",
        "carrier",
        "compute_class",
        "model_profile",
        "standard_value_case_status",
        "frontier_value_gate_status",
        "owner_frontier_authorized",
        "frontier_gate_condition",
        "bounded_question_set_digest",
        "fallback_if_frontier_unavailable",
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
            "fresh_trust_gate: duplicate compute authorization YAML keys: "
            + ", ".join(duplicates)
        )


def _secure_build_verified_compute_lane_authorization(
    repo_path: str | Path, authorization_ref: str
) -> base.VerifiedComputeLaneAuthorization:
    """Build compute authority only through the bridge-owned protected transport."""
    base._validate_ref(authorization_ref)
    canonical_main_sha, read = _protected_open(repo_path)
    raw = read(authorization_ref)
    text = raw.decode("utf-8")
    _reject_duplicate_compute_yaml_keys(text)

    required = (
        *base.COMMON_IDENTITY_FIELDS,
        "authorization_status",
        "executor",
        "carrier",
        "compute_class",
        "model_profile",
    )
    payload: dict[str, Any] = {key: base._scalar(text, key) for key in required}
    if payload["control_plane_repository"] != base.TRUSTED_CONTROL_PLANE_REPOSITORY:
        raise ExecutionContractError("compute_authorization: wrong control-plane repository")
    if payload["authorization_status"] != "AUTHORIZED":
        raise ExecutionContractError("compute_authorization: authorization is not AUTHORIZED")
    if payload["carrier"] not in base._CODEX_CARRIERS:
        raise ExecutionContractError(
            "compute_authorization: only governed Codex lanes use this authority"
        )

    base._validate_compute_selection(payload, require_runtime_model=False)

    if payload["carrier"] == "CODEX_STANDARD_ESCALATION":
        payload["standard_value_case_status"] = base._scalar(
            text, "standard_value_case_status"
        )
        if payload["standard_value_case_status"] != "PASS":
            raise ExecutionContractError(
                "compute_authorization: Codex Standard value case not PASS"
            )
    else:
        payload["frontier_value_gate_status"] = base._scalar(
            text, "frontier_value_gate_status"
        )
        payload["owner_frontier_authorized"] = base._scalar(
            text, "owner_frontier_authorized"
        )
        payload["frontier_gate_condition"] = base._scalar(
            text, "frontier_gate_condition"
        )
        payload["bounded_question_set_digest"] = base._scalar(
            text, "bounded_question_set_digest"
        )
        payload["fallback_if_frontier_unavailable"] = base._scalar(
            text, "fallback_if_frontier_unavailable"
        )
        if payload["frontier_value_gate_status"] != "PASS":
            raise ExecutionContractError("compute_authorization: frontier value gate not PASS")
        if payload["owner_frontier_authorized"] is not True:
            raise ExecutionContractError(
                "compute_authorization: Owner frontier authorization missing"
            )
        if payload["frontier_gate_condition"] not in base._FRONTIER_GATE_CONDITIONS:
            raise ExecutionContractError(
                "compute_authorization: invalid frontier gate condition"
            )
        if not str(payload["bounded_question_set_digest"]).strip():
            raise ExecutionContractError(
                "compute_authorization: bounded question set digest missing"
            )
        if not str(payload["fallback_if_frontier_unavailable"]).strip():
            raise ExecutionContractError(
                "compute_authorization: frontier fallback missing"
            )

    payload["canonical_main_sha"] = canonical_main_sha
    payload["authorization_ref"] = authorization_ref
    payload["authorization_document_digest"] = base._sha(raw)
    payload["compute_authorization_receipt_digest"] = base._json_digest(payload)
    return base._issue_compute_authorization(payload)


def _fresh_compute_lane_authorization(
    repo_path: str | Path, authorization_ref: str
) -> base.VerifiedComputeLaneAuthorization:
    fresh = _secure_build_verified_compute_lane_authorization(repo_path, authorization_ref)
    mapping = _compute_mapping(fresh)
    base.validate_compute_lane_authorization(fresh)
    _terminal_remote_main_recheck(repo_path, str(mapping["canonical_main_sha"]))
    return fresh


def validate_compute_lane_authorization(
    repo_path: str | Path,
    authorization_ref: str,
    claimed_snapshot: base.VerifiedComputeLaneAuthorization,
) -> base.VerifiedComputeLaneAuthorization:
    claimed = _compute_mapping(claimed_snapshot)
    fresh = _fresh_compute_lane_authorization(repo_path, authorization_ref)
    canonical = _compute_mapping(fresh)
    if not _same_snapshot(claimed, canonical):
        raise ExecutionContractError(
            "fresh_trust_gate: claimed compute authorization differs from fresh canonical state"
        )
    return fresh


def _resolve_fresh_compute_for_dispatch(
    repo_path: str | Path,
    dispatch: Mapping[str, Any],
    fresh_authority: base.VerifiedCanonicalAuthority,
    compute_authorization_ref: str | None,
    claimed_compute_authorization: base.VerifiedComputeLaneAuthorization | None,
) -> base.VerifiedComputeLaneAuthorization | None:
    carrier = dispatch.get("carrier")
    requires_compute = carrier in base._CODEX_CARRIERS
    if not requires_compute:
        if compute_authorization_ref is not None or claimed_compute_authorization is not None:
            raise ExecutionContractError(
                "fresh_trust_gate: non-Codex dispatch cannot consume Codex compute authorization"
            )
        return None
    if not compute_authorization_ref or claimed_compute_authorization is None:
        raise ExecutionContractError(
            "fresh_trust_gate: Codex process-start requires canonical compute authorization"
        )
    fresh_compute = validate_compute_lane_authorization(
        repo_path, compute_authorization_ref, claimed_compute_authorization
    )
    compute = _compute_mapping(fresh_compute)
    authority = _authority_mapping(fresh_authority)
    base._same_identity(compute, authority, "fresh_trust_gate.compute_authority")
    if compute["canonical_main_sha"] != authority["canonical_main_sha"]:
        raise ExecutionContractError(
            "fresh_trust_gate: compute and writer authority are from different main states"
        )
    return fresh_compute


def validate_dispatch(
    repo_path: str | Path,
    dispatch: Mapping[str, Any],
    claimed_snapshot: base.VerifiedCanonicalAuthority,
    compute_authorization_ref: str | None = None,
    claimed_compute_authorization: base.VerifiedComputeLaneAuthorization | None = None,
) -> base.VerifiedCanonicalAuthority:
    fresh = validate_canonical_authority(repo_path, claimed_snapshot)
    fresh_compute = _resolve_fresh_compute_for_dispatch(
        repo_path,
        dispatch,
        fresh,
        compute_authorization_ref,
        claimed_compute_authorization,
    )
    base.validate_dispatch(dispatch, fresh, fresh_compute)
    return fresh


def validate_local_admission(
    repo_path: str | Path,
    admission: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    claimed_snapshot: base.VerifiedCanonicalAuthority,
    compute_authorization_ref: str | None = None,
    claimed_compute_authorization: base.VerifiedComputeLaneAuthorization | None = None,
) -> base.VerifiedCanonicalAuthority:
    fresh = validate_canonical_authority(repo_path, claimed_snapshot)
    fresh_compute = _resolve_fresh_compute_for_dispatch(
        repo_path,
        dispatch,
        fresh,
        compute_authorization_ref,
        claimed_compute_authorization,
    )
    base.validate_local_admission(admission, dispatch, fresh, fresh_compute)
    return fresh


def validate_process_start(
    repo_path: str | Path,
    admission: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    claimed_snapshot: base.VerifiedCanonicalAuthority,
    compute_authorization_ref: str | None = None,
    claimed_compute_authorization: base.VerifiedComputeLaneAuthorization | None = None,
) -> base.VerifiedCanonicalAuthority:
    return validate_local_admission(
        repo_path,
        admission,
        dispatch,
        claimed_snapshot,
        compute_authorization_ref,
        claimed_compute_authorization,
    )


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
    old_compute_authorization_snapshot: base.VerifiedComputeLaneAuthorization | None = None,
    new_compute_authorization_ref: str | None = None,
    new_compute_authorization_snapshot: base.VerifiedComputeLaneAuthorization | None = None,
) -> None:
    fresh_new = validate_local_admission(
        repo_path,
        new_admission,
        new_dispatch,
        new_authority_snapshot,
        new_compute_authorization_ref,
        new_compute_authorization_snapshot,
    )
    fresh_release = validate_release_witness(repo_path, release_ref, release_snapshot)
    if (
        _release_mapping(fresh_release)["canonical_main_sha"]
        != _authority_mapping(fresh_new)["canonical_main_sha"]
    ):
        raise ExecutionContractError(
            "fresh_trust_gate: release and new admission are from different main states"
        )

    fresh_new_compute = None
    if new_dispatch.get("carrier") in base._CODEX_CARRIERS:
        fresh_new_compute = validate_compute_lane_authorization(
            repo_path,
            str(new_compute_authorization_ref),
            new_compute_authorization_snapshot,
        )

    if old_dispatch.get("carrier") in base._CODEX_CARRIERS:
        if old_compute_authorization_snapshot is None:
            raise ExecutionContractError(
                "fresh_trust_gate: Codex old writer requires its admitted compute authorization"
            )
        base.validate_compute_lane_authorization(old_compute_authorization_snapshot)

    base.validate_carrier_handoff(
        handoff,
        old_dispatch,
        old_authority_snapshot,
        fresh_release,
        new_dispatch,
        new_admission,
        fresh_new,
        old_compute_authorization_snapshot,
        fresh_new_compute,
    )
