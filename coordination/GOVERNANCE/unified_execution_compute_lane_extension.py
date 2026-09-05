"""Executable compute-lane hardening layered over the canonical execution validator.

The legacy implementation is executed into this module's globals so existing trust-boundary
semantics and monkey-patch based tests remain intact. This extension only adds first-class
Codex Standard/Frontier carrier identity plus fail-closed compute-lane authorization.
"""
from pathlib import Path as _BootstrapPath

_base_path = _BootstrapPath(__file__).with_name("unified_execution_validation_base.py")
exec(compile(_base_path.read_text(encoding="utf-8"), str(_base_path), "exec"), globals(), globals())
del _base_path, _BootstrapPath

# Preserve the pre-extension validator for composition.
_legacy_validate_dispatch = validate_dispatch

GLOBAL_CARRIERS = set(GLOBAL_CARRIERS) | {"CODEX_STANDARD_ESCALATION"}

COMPUTE_LANE_FIELDS = (
    "executor",
    "carrier",
    "compute_class",
    "model_profile",
    "resolved_model_display_name",
    "model_resolution_status",
    "compute_lane_receipt_digest",
)

_CARRIER_COMPUTE_CLASS = {
    "GPT_DIRECT": "STANDARD",
    "WORKBUDDY_CLI_HEADLESS": "STANDARD",
    "WORKBUDDY_CLI_WEBUI": "STANDARD",
    "WORKBUDDY_DESKTOP_INTERACTIVE": "STANDARD",
    "CODEX_STANDARD_ESCALATION": "STANDARD",
    "CODEX_FRONTIER_ESCALATION": "FRONTIER",
}

_EXECUTOR_BY_CARRIER = {
    "GPT_DIRECT": "GPT_ARCHITECTURE_OWNER",
    "WORKBUDDY_CLI_HEADLESS": "WORKBUDDY_ENGINEERING_EXECUTOR",
    "WORKBUDDY_CLI_WEBUI": "WORKBUDDY_ENGINEERING_EXECUTOR",
    "WORKBUDDY_DESKTOP_INTERACTIVE": "WORKBUDDY_ENGINEERING_EXECUTOR",
    "CODEX_STANDARD_ESCALATION": "CODEX_STANDARD_ENGINEER",
    "CODEX_FRONTIER_ESCALATION": "CODEX_FRONTIER_ARCHITECT",
}

_CODEX_CARRIERS = {"CODEX_STANDARD_ESCALATION", "CODEX_FRONTIER_ESCALATION"}
_FRONTIER_GATE_CONDITIONS = {
    "ARCHITECTURE_LEVERAGE",
    "IRREVERSIBLE_OR_HIGH_REWORK_COST",
    "FRONTIER_AMBIGUITY",
    "CROSS_DOMAIN_SYNTHESIS",
    "HIGH_RISK_CORRECTNESS",
    "ROOT_CAUSE_ESCALATION",
}

@dataclass(frozen=True)
class VerifiedComputeLaneAuthorization:
    _payload: Mapping[str, Any]
    _issuer: object

    def as_mapping(self) -> Mapping[str, Any]:
        if self._issuer is not _ISSUER:
            raise ExecutionContractError("compute_authorization: untrusted issuer")
        return self._payload


def _issue_compute_authorization(payload: Mapping[str, Any]) -> VerifiedComputeLaneAuthorization:
    return VerifiedComputeLaneAuthorization(_freeze(payload), _ISSUER)


def _compute_authorization_mapping(
    authorization: VerifiedComputeLaneAuthorization,
) -> Mapping[str, Any]:
    if not isinstance(authorization, VerifiedComputeLaneAuthorization):
        raise ExecutionContractError(
            "compute_authorization: caller-supplied mapping is not trusted authorization"
        )
    return authorization.as_mapping()


def _validate_compute_selection(mapping: Mapping[str, Any], *, require_runtime_model: bool) -> None:
    required = ("executor", "carrier", "compute_class", "model_profile")
    if require_runtime_model:
        required += ("resolved_model_display_name", "model_resolution_status")
    _require(mapping, required, "compute_lane")

    carrier = mapping["carrier"]
    if carrier not in GLOBAL_CARRIERS:
        raise ExecutionContractError(f"compute_lane: unknown carrier {carrier}")
    expected_class = _CARRIER_COMPUTE_CLASS.get(carrier)
    if mapping["compute_class"] != expected_class:
        raise ExecutionContractError("compute_lane: compute_class does not match carrier")
    if mapping["executor"] != _EXECUTOR_BY_CARRIER.get(carrier):
        raise ExecutionContractError("compute_lane: executor does not match carrier")

    if carrier == "CODEX_STANDARD_ESCALATION":
        if mapping["model_profile"] != "CODEX_STANDARD_ENGINEERING":
            raise ExecutionContractError("compute_lane: Codex Standard requires CODEX_STANDARD_ENGINEERING")
    elif carrier == "CODEX_FRONTIER_ESCALATION":
        if mapping["model_profile"] != "FRONTIER_ARCHITECTURE":
            raise ExecutionContractError("compute_lane: Codex Frontier requires FRONTIER_ARCHITECTURE")
    elif mapping["model_profile"] in {"CODEX_STANDARD_ENGINEERING", "FRONTIER_ARCHITECTURE"}:
        raise ExecutionContractError("compute_lane: Codex-only profile used by non-Codex carrier")

    if require_runtime_model:
        if mapping["model_resolution_status"] != "RESOLVED":
            raise ExecutionContractError("compute_lane: executable dispatch requires resolved model")
        if not str(mapping["resolved_model_display_name"]).strip():
            raise ExecutionContractError("compute_lane: resolved model identity is empty")


def build_verified_compute_lane_authorization(
    repo_path: str | Path, authorization_ref: str
) -> VerifiedComputeLaneAuthorization:
    """Fresh-read a task-bound Standard/Frontier authorization from canonical main."""
    _validate_ref(authorization_ref)
    canonical_main_sha, read = _open_trusted_main(repo_path)
    raw = read(authorization_ref)
    text = raw.decode("utf-8")
    required = (
        *COMMON_IDENTITY_FIELDS,
        "authorization_status",
        "executor",
        "carrier",
        "compute_class",
        "model_profile",
    )
    payload: dict[str, Any] = {key: _scalar(text, key) for key in required}
    if payload["control_plane_repository"] != TRUSTED_CONTROL_PLANE_REPOSITORY:
        raise ExecutionContractError("compute_authorization: wrong control-plane repository")
    if payload["authorization_status"] != "AUTHORIZED":
        raise ExecutionContractError("compute_authorization: authorization is not AUTHORIZED")
    if payload["carrier"] not in _CODEX_CARRIERS:
        raise ExecutionContractError("compute_authorization: only governed Codex lanes use this authority")

    _validate_compute_selection(payload, require_runtime_model=False)

    if payload["carrier"] == "CODEX_STANDARD_ESCALATION":
        payload["standard_value_case_status"] = _scalar(text, "standard_value_case_status")
        if payload["standard_value_case_status"] != "PASS":
            raise ExecutionContractError("compute_authorization: Codex Standard value case not PASS")
    else:
        payload["frontier_value_gate_status"] = _scalar(text, "frontier_value_gate_status")
        payload["owner_frontier_authorized"] = _scalar(text, "owner_frontier_authorized")
        payload["frontier_gate_condition"] = _scalar(text, "frontier_gate_condition")
        payload["bounded_question_set_digest"] = _scalar(text, "bounded_question_set_digest")
        payload["fallback_if_frontier_unavailable"] = _scalar(text, "fallback_if_frontier_unavailable")
        if payload["frontier_value_gate_status"] != "PASS":
            raise ExecutionContractError("compute_authorization: frontier value gate not PASS")
        if payload["owner_frontier_authorized"] is not True:
            raise ExecutionContractError("compute_authorization: Owner frontier authorization missing")
        if payload["frontier_gate_condition"] not in _FRONTIER_GATE_CONDITIONS:
            raise ExecutionContractError("compute_authorization: invalid frontier gate condition")
        if not str(payload["bounded_question_set_digest"]).strip():
            raise ExecutionContractError("compute_authorization: bounded question set digest missing")

    payload["canonical_main_sha"] = canonical_main_sha
    payload["authorization_ref"] = authorization_ref
    payload["authorization_document_digest"] = _sha(raw)
    receipt_material = dict(payload)
    payload["compute_authorization_receipt_digest"] = _json_digest(receipt_material)
    return _issue_compute_authorization(payload)


def validate_compute_lane_authorization(
    authorization: VerifiedComputeLaneAuthorization,
) -> None:
    mapping = _compute_authorization_mapping(authorization)
    _require(
        mapping,
        (*COMMON_IDENTITY_FIELDS, "authorization_status", "executor", "carrier", "compute_class",
         "model_profile", "canonical_main_sha", "authorization_ref", "authorization_document_digest",
         "compute_authorization_receipt_digest"),
        "compute_authorization",
    )
    material = {key: value for key, value in mapping.items() if key != "compute_authorization_receipt_digest"}
    if mapping["compute_authorization_receipt_digest"] != _json_digest(material):
        raise ExecutionContractError("compute_authorization: receipt recomputation failed")
    _validate_compute_selection(mapping, require_runtime_model=False)


def _compute_lane_material(dispatch: Mapping[str, Any]) -> Mapping[str, Any]:
    keys = [
        "executor",
        "carrier",
        "compute_class",
        "model_profile",
        "resolved_model_display_name",
        "model_resolution_status",
    ]
    if dispatch.get("carrier") in _CODEX_CARRIERS:
        keys.extend(("compute_authorization_ref", "compute_authorization_receipt_digest"))
    return {key: dispatch.get(key) for key in keys}


def compute_lane_receipt_digest(dispatch: Mapping[str, Any]) -> str:
    """Public deterministic helper for producers/tests; not an authority by itself."""
    return _json_digest(_compute_lane_material(dispatch))


def _validate_compute_dispatch(
    dispatch: Mapping[str, Any],
    canonical: Mapping[str, Any],
    compute_authorization: VerifiedComputeLaneAuthorization | None,
) -> None:
    _require(dispatch, COMPUTE_LANE_FIELDS, "dispatch.compute_lane")
    _validate_compute_selection(dispatch, require_runtime_model=True)
    if dispatch["compute_lane_receipt_digest"] != compute_lane_receipt_digest(dispatch):
        raise ExecutionContractError("dispatch: compute lane receipt mismatch")

    carrier = dispatch["carrier"]
    if carrier in _CODEX_CARRIERS:
        if compute_authorization is None:
            raise ExecutionContractError("dispatch: governed Codex lane requires verified compute authorization")
        validate_compute_lane_authorization(compute_authorization)
        authorized = _compute_authorization_mapping(compute_authorization)
        _same_identity(authorized, canonical, "compute_authorization.canonical")
        if authorized["canonical_main_sha"] != canonical["canonical_main_sha"]:
            raise ExecutionContractError("dispatch: compute authorization not from canonical authority main")
        for field in ("executor", "carrier", "compute_class", "model_profile"):
            if dispatch[field] != authorized[field]:
                raise ExecutionContractError(f"dispatch: {field} not authorized by compute lane authority")
        _require(
            dispatch,
            ("compute_authorization_ref", "compute_authorization_receipt_digest"),
            "dispatch.compute_authorization",
        )
        if dispatch["compute_authorization_ref"] != authorized["authorization_ref"]:
            raise ExecutionContractError("dispatch: compute authorization ref mismatch")
        if dispatch["compute_authorization_receipt_digest"] != authorized["compute_authorization_receipt_digest"]:
            raise ExecutionContractError("dispatch: compute authorization receipt mismatch")
    else:
        if compute_authorization is not None:
            raise ExecutionContractError("dispatch: non-Codex carrier cannot consume Codex compute authorization")


def validate_dispatch(
    dispatch: Mapping[str, Any],
    canonical_authority: VerifiedCanonicalAuthority,
    compute_authorization: VerifiedComputeLaneAuthorization | None = None,
) -> None:
    _legacy_validate_dispatch(dispatch, canonical_authority)
    canonical = _authority_mapping(canonical_authority)
    _validate_compute_dispatch(dispatch, canonical, compute_authorization)


def validate_local_admission(
    admission: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    canonical_authority: VerifiedCanonicalAuthority,
    compute_authorization: VerifiedComputeLaneAuthorization | None = None,
) -> None:
    validate_dispatch(dispatch, canonical_authority, compute_authorization)
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
            "writer_lease_identity",
        )
        + COMPUTE_LANE_FIELDS,
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
        "writer_lease_identity",
        *COMPUTE_LANE_FIELDS,
    ):
        if admission[field] != dispatch[field]:
            raise ExecutionContractError(f"local_admission: {field} does not match dispatch")
    if admission["writer_lease_identity"] != canonical["writer_lease_identity"]:
        raise ExecutionContractError("local_admission: writer lease identity is not canonical")
    if dispatch["carrier"] in _CODEX_CARRIERS:
        for field in ("compute_authorization_ref", "compute_authorization_receipt_digest"):
            if admission.get(field) != dispatch.get(field):
                raise ExecutionContractError(f"local_admission: {field} does not match dispatch")


def validate_carrier_handoff(
    handoff: Mapping[str, Any],
    old_dispatch: Mapping[str, Any],
    old_authority: VerifiedCanonicalAuthority,
    release_witness: VerifiedReleaseWitness,
    new_dispatch: Mapping[str, Any],
    new_admission: Mapping[str, Any],
    new_authority: VerifiedCanonicalAuthority,
    old_compute_authorization: VerifiedComputeLaneAuthorization | None = None,
    new_compute_authorization: VerifiedComputeLaneAuthorization | None = None,
) -> None:
    validate_dispatch(old_dispatch, old_authority, old_compute_authorization)
    validate_local_admission(new_admission, new_dispatch, new_authority, new_compute_authorization)
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
            "old_writer_lease_identity",
            "new_writer_admission_required",
        ),
        "carrier_handoff",
    )
    _same_identity(handoff, old_dispatch, "carrier_handoff.old_dispatch")
    _same_identity(new_dispatch, old_dispatch, "carrier_handoff.new_dispatch")
    if handoff["from_carrier"] != old_dispatch["carrier"] or handoff["to_carrier"] != new_dispatch["carrier"]:
        raise ExecutionContractError("carrier_handoff: carrier identity does not match dispatches")
    if handoff["new_writer_admission_required"] is not True:
        raise ExecutionContractError("carrier_handoff: new writer admission must be required")
    for field in COMMON_IDENTITY_FIELDS:
        if release[field] != handoff[field]:
            raise ExecutionContractError(f"carrier_handoff: release identity mismatch: {field}")
    if handoff["old_writer_lease_identity"] != old["writer_lease_identity"]:
        raise ExecutionContractError("carrier_handoff: old writer lease identity mismatch")
    if release["writer_lease_identity"] != old["writer_lease_identity"]:
        raise ExecutionContractError("carrier_handoff: release did not release old canonical writer")
    if release["writer_lease_ref"] != old["authority_refs"]["task_lease_ref"]:
        raise ExecutionContractError("carrier_handoff: released lease ref does not match old canonical authority")
    if release["released_lease_digest"] != old["authority_digests"]["task_lease_ref"]:
        raise ExecutionContractError("carrier_handoff: released lease digest does not match old canonical authority")
    if release["canonical_main_sha"] != new["canonical_main_sha"]:
        raise ExecutionContractError("carrier_handoff: release witness is not from new admission main")
    if new["authority_digests"]["task_lease_ref"] == old["authority_digests"]["task_lease_ref"]:
        raise ExecutionContractError("carrier_handoff: new writer reused old lease document")
    if new["writer_lease_identity"] == old["writer_lease_identity"]:
        raise ExecutionContractError("carrier_handoff: old writer lease replayed")
    if new_admission["writer_lease_identity"] != new["writer_lease_identity"]:
        raise ExecutionContractError("carrier_handoff: new admission is not bound to canonical new writer lease")
