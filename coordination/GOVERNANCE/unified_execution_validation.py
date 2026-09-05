"""Dependency-free validators for the unified execution fabric governance contracts."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


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


def _nonempty_digest_map(mapping: Mapping[str, Any], label: str) -> None:
    _require(mapping, AUTHORITY_REF_FIELDS, label)
    for field in AUTHORITY_REF_FIELDS:
        value = mapping[field]
        if not isinstance(value, str) or len(value.strip()) < 8:
            raise ExecutionContractError(f"{label}: invalid authority reference/digest for {field}")


def validate_canonical_authority(authority: Mapping[str, Any]) -> None:
    _require(
        authority,
        COMMON_IDENTITY_FIELDS
        + (
            "canonical_main_sha",
            "authority_chain_receipt_digest",
            "authority_refs",
            "authority_digests",
            "route_status",
            "execution_allowed",
            "lease_released",
            "lease_replaced",
            "authority_replaced",
            "fresh_readback",
            "authorized_paths",
            "authority_grants",
            "authority_denials",
        ),
        "canonical_authority",
    )
    if authority["route_status"] != "READY":
        raise ExecutionContractError("canonical_authority: route is not READY")
    if authority["execution_allowed"] is not True:
        raise ExecutionContractError("canonical_authority: execution is not allowed")
    if authority["fresh_readback"] is not True:
        raise ExecutionContractError("canonical_authority: readback is not fresh")
    if authority["lease_released"] is True:
        raise ExecutionContractError("canonical_authority: lease is released")
    if authority["lease_replaced"] is True:
        raise ExecutionContractError("canonical_authority: lease is replaced")
    if authority["authority_replaced"] is True:
        raise ExecutionContractError("canonical_authority: authority chain is replaced")
    _nonempty_digest_map(authority["authority_refs"], "canonical_authority.authority_refs")
    _nonempty_digest_map(authority["authority_digests"], "canonical_authority.authority_digests")


def validate_dispatch(dispatch: Mapping[str, Any], canonical_authority: Mapping[str, Any]) -> None:
    validate_canonical_authority(canonical_authority)
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
    _same_identity(dispatch, canonical_authority, "dispatch")
    if dispatch["canonical_main_sha"] != canonical_authority["canonical_main_sha"]:
        raise ExecutionContractError("dispatch: canonical main moved")
    if dispatch["authority_chain_receipt_digest"] != canonical_authority["authority_chain_receipt_digest"]:
        raise ExecutionContractError("dispatch: authority receipt digest mismatch")
    if dispatch["authority_refs"] != canonical_authority["authority_refs"]:
        raise ExecutionContractError("dispatch: authority refs mismatch")
    if dispatch["authority_digests"] != canonical_authority["authority_digests"]:
        raise ExecutionContractError("dispatch: authority digests mismatch")

    canonical_paths = set(canonical_authority["authorized_paths"])
    requested_paths = set(dispatch["authorized_paths"])
    if not requested_paths <= canonical_paths:
        raise ExecutionContractError("dispatch: authorized paths exceed canonical authority")

    canonical_grants = set(canonical_authority["authority_grants"])
    requested_grants = set(dispatch["authority_grants"])
    if not requested_grants <= canonical_grants:
        raise ExecutionContractError("dispatch: authority grants exceed canonical authority")

    canonical_denials = set(canonical_authority["authority_denials"])
    requested_denials = set(dispatch["authority_denials"])
    if not canonical_denials <= requested_denials:
        raise ExecutionContractError("dispatch: canonical authority denials were weakened")


def validate_local_admission(
    admission: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    canonical_authority: Mapping[str, Any],
) -> None:
    validate_dispatch(dispatch, canonical_authority)
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
            "admitted",
        ),
        "local_admission",
    )
    _same_identity(admission, dispatch, "local_admission.dispatch")
    _same_identity(admission, canonical_authority, "local_admission.canonical_authority")

    if admission["route_status"] != "READY":
        raise ExecutionContractError("local_admission: route_status must be READY")
    if admission["execution_allowed"] is not True:
        raise ExecutionContractError("local_admission: execution_allowed must be true")
    if admission["admitted"] is not True:
        raise ExecutionContractError("local_admission: admission not granted")
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
            raise ExecutionContractError(f"local_admission: {field} does not match dispatch")


def validate_carrier_handoff(
    handoff: Mapping[str, Any],
    release_witness: Mapping[str, Any],
    new_admission: Mapping[str, Any],
) -> None:
    _require(
        handoff,
        COMMON_IDENTITY_FIELDS
        + (
            "from_carrier",
            "to_carrier",
            "checkpoint_head_sha",
            "old_writer_lease_id",
            "old_writer_lease_generation",
            "old_writer_release_receipt_digest",
            "release_readback_canonical_main_sha",
            "new_writer_admission_required",
        ),
        "carrier_handoff",
    )
    _same_identity(handoff, release_witness, "carrier_handoff.release_witness")
    _same_identity(handoff, new_admission, "carrier_handoff.new_admission")
    _require(
        release_witness,
        (
            "writer_lease_id",
            "writer_lease_generation",
            "release_status",
            "release_receipt_digest",
            "canonical_readback_verified",
            "canonical_main_sha",
        ),
        "release_witness",
    )
    if release_witness["release_status"] != "RELEASED":
        raise ExecutionContractError("carrier_handoff: old writer lease is not canonically released")
    if release_witness["canonical_readback_verified"] is not True:
        raise ExecutionContractError("carrier_handoff: release witness lacks canonical readback")
    if release_witness["writer_lease_id"] != handoff["old_writer_lease_id"]:
        raise ExecutionContractError("carrier_handoff: old lease id mismatch")
    if release_witness["writer_lease_generation"] != handoff["old_writer_lease_generation"]:
        raise ExecutionContractError("carrier_handoff: old lease generation mismatch")
    if release_witness["release_receipt_digest"] != handoff["old_writer_release_receipt_digest"]:
        raise ExecutionContractError("carrier_handoff: release receipt mismatch")
    if release_witness["canonical_main_sha"] != handoff["release_readback_canonical_main_sha"]:
        raise ExecutionContractError("carrier_handoff: release readback main mismatch")
    if handoff["new_writer_admission_required"] is not True:
        raise ExecutionContractError("carrier_handoff: new writer admission must be required")

    _require(new_admission, ("admitted", "writer_lease_id", "writer_lease_generation"), "new_admission")
    if new_admission["admitted"] is not True:
        raise ExecutionContractError("carrier_handoff: new writer is not admitted")
    if new_admission["writer_lease_id"] == handoff["old_writer_lease_id"]:
        raise ExecutionContractError("carrier_handoff: old writer lease cannot be replayed")


def validate_project_adapter(adapter: Mapping[str, Any], global_policy: Mapping[str, Any]) -> None:
    _require(
        adapter,
        (
            "project_id",
            "global_protocol_id",
            "inherits_global_invariants",
            "control_plane_repository",
            "execution_repository",
            "allowed_execution_carriers",
        ),
        "project_adapter",
    )
    _require(global_policy, ("protocol_id", "allowed_execution_carriers", "non_weakenable_invariants"), "global_policy")

    if adapter["global_protocol_id"] != global_policy["protocol_id"]:
        raise ExecutionContractError("project_adapter: wrong global protocol")
    if adapter["inherits_global_invariants"] is not True:
        raise ExecutionContractError("project_adapter: global invariants must be inherited")

    extra_carriers = set(adapter["allowed_execution_carriers"]) - set(global_policy["allowed_execution_carriers"])
    if extra_carriers:
        raise ExecutionContractError("project_adapter: carrier set exceeds global policy")

    overrides = adapter.get("global_invariant_overrides", {})
    for invariant in set(global_policy["non_weakenable_invariants"]) | NON_WEAKENABLE_INVARIANTS:
        if invariant in overrides and overrides[invariant] is not True:
            raise ExecutionContractError(f"project_adapter: invariant weakened: {invariant}")

    if "global_router" in adapter or "global_task_router" in adapter:
        raise ExecutionContractError("project_adapter: second global router is forbidden")
