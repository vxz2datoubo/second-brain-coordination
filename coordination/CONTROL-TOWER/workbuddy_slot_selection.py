"""Fail-closed selection and runtime-binding validation for projected WorkBuddy slots.

Selection is not process-start authority. Runtime envelopes are structurally checked and
bound to one canonical slot, but this Stage-2 module deliberately cannot authorize a
physical WorkBuddy process. A later separately governed canary/runtime gate must consume
trusted scheduler, process-ownership and teardown evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

try:
    import workbuddy_slots as slots
except ModuleNotFoundError:  # loaded together by the sibling CLI/test harness
    slots = None  # type: ignore[assignment]

SELECTION_SCHEMA = "WORKBUDDY_SLOT_SELECTION_RESULT/v1"
RUNTIME_BINDING_SCHEMA = "WORKBUDDY_RUNTIME_BINDING/v1"
WORKTREE_EXPECTATION_SCHEMA = "WORKBUDDY_EXPECTED_WORKTREE_BINDING/v1"
SELECTED = "SELECTED"
AMBIGUOUS = "AMBIGUOUS_WORKBUDDY_SLOT_SELECTION"
NO_ELIGIBLE = "NO_ELIGIBLE_WORKBUDDY_SLOT"
NOT_FOUND = "EXPLICIT_WORKBUDDY_SLOT_NOT_FOUND"
CONFLICTING_SELECTOR = "CONFLICTING_EXPLICIT_WORKBUDDY_SELECTORS"
PROCESS_START_BLOCKED = "PROCESS_START_BLOCKED_PENDING_SEPARATE_PHYSICAL_CANARY_GATE"


class SlotSelectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class SelectionResult:
    schema: str
    status: str
    canonical_main_sha: str | None
    selected_worker_slot_id: str | None
    selected_task_id: str | None
    candidate_count: int
    explicit_selector_used: bool
    process_start_authorized: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeBindingResult:
    schema: str
    status: str
    canonical_main_sha: str
    worker_slot_id: str
    task_id: str
    executor_id: str
    run_id: str
    worktree_id: str
    worktree_path_digest: str
    authority_chain_receipt_digest: str
    writer_lease_identity: str
    acquired_resource_lease_ids: tuple[str, ...]
    process_ownership_status: str
    carrier_teardown_capability: str
    binding_digest: str
    process_start_authorized: bool
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["acquired_resource_lease_ids"] = list(self.acquired_resource_lease_ids)
        value["blockers"] = list(self.blockers)
        return value


def _slot_mapping(slot: Any) -> Mapping[str, Any]:
    if hasattr(slot, "as_dict"):
        value = slot.as_dict()
    elif isinstance(slot, Mapping):
        value = dict(slot)
    else:
        raise SlotSelectionError("workbuddy_slot_selection: malformed slot object")
    if not isinstance(value, Mapping):
        raise SlotSelectionError("workbuddy_slot_selection: malformed slot mapping")
    return value


def _declared_candidates(slot_values: Sequence[Any]) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in slot_values:
        current = _slot_mapping(raw)
        worker_slot_id = current.get("worker_slot_id")
        task_id = current.get("task_id")
        if not isinstance(worker_slot_id, str) or not worker_slot_id:
            raise SlotSelectionError("workbuddy_slot_selection: slot missing worker_slot_id")
        if worker_slot_id in seen_ids:
            raise SlotSelectionError("workbuddy_slot_selection: duplicate worker_slot_id")
        seen_ids.add(worker_slot_id)
        if not isinstance(task_id, str) or not task_id:
            raise SlotSelectionError("workbuddy_slot_selection: slot missing task_id")
        state = current.get("logical_state")
        if state == "DECLARED":
            result.append(current)
        elif state == "BLOCKED":
            continue
        else:
            continue  # unknown/typo states never become executable by default
    return result


def select_workbuddy_slot(
    slot_values: Sequence[Any], *, task_id: str | None = None,
    worker_slot_id: str | None = None,
) -> SelectionResult:
    """Select one logical slot without minting process-start authority."""
    candidates = _declared_candidates(slot_values)
    main_values = {str(item.get("canonical_main_sha")) for item in candidates}
    canonical_main_sha = next(iter(main_values)) if len(main_values) == 1 else None
    if len(main_values) > 1:
        raise SlotSelectionError("workbuddy_slot_selection: candidates span canonical-main snapshots")

    explicit = task_id is not None or worker_slot_id is not None
    if not explicit:
        if len(candidates) == 1:
            selected = candidates[0]
            return SelectionResult(
                SELECTION_SCHEMA, SELECTED, canonical_main_sha,
                str(selected["worker_slot_id"]), str(selected["task_id"]), 1, False,
                False, "unique declared slot selected; process start remains separately gated",
            )
        if len(candidates) == 0:
            return SelectionResult(
                SELECTION_SCHEMA, NO_ELIGIBLE, canonical_main_sha, None, None, 0, False,
                False, "no declared WorkBuddy slot is selectable",
            )
        return SelectionResult(
            SELECTION_SCHEMA, AMBIGUOUS, canonical_main_sha, None, None,
            len(candidates), False, False,
            "multiple legal WorkBuddy slots require an explicit selector",
        )

    matches = candidates
    if task_id is not None:
        if not isinstance(task_id, str) or not task_id:
            raise SlotSelectionError("workbuddy_slot_selection: empty task selector")
        matches = [item for item in matches if item.get("task_id") == task_id]
    if worker_slot_id is not None:
        if not isinstance(worker_slot_id, str) or not worker_slot_id:
            raise SlotSelectionError("workbuddy_slot_selection: empty worker-slot selector")
        prior = matches
        matches = [item for item in matches if item.get("worker_slot_id") == worker_slot_id]
        if task_id is not None and prior and not matches:
            return SelectionResult(
                SELECTION_SCHEMA, CONFLICTING_SELECTOR, canonical_main_sha,
                None, None, len(candidates), True, False,
                "task_id and worker_slot_id do not identify the same canonical slot",
            )

    if len(matches) != 1:
        return SelectionResult(
            SELECTION_SCHEMA, NOT_FOUND, canonical_main_sha, None, None,
            len(candidates), True, False,
            "explicit selector did not resolve exactly one declared canonical slot",
        )
    selected = matches[0]
    return SelectionResult(
        SELECTION_SCHEMA, SELECTED, canonical_main_sha,
        str(selected["worker_slot_id"]), str(selected["task_id"]),
        len(candidates), True, False,
        "explicit selector resolved one canonical slot; process start remains separately gated",
    )


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SlotSelectionError(f"runtime_admission: {label} must be a non-empty string")
    return value.strip()


def _require_sha256_digest(value: Any, label: str) -> str:
    text = _require_nonempty_string(value, label)
    if not re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", text):
        raise SlotSelectionError(f"runtime_admission: {label} must be a SHA-256 digest")
    return text


def _sha256_digest_hex(value: Any, label: str) -> str:
    text = _require_sha256_digest(value, label)
    return text[len("sha256:"):] if text.startswith("sha256:") else text


def _canonical_json_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + sha256(payload).hexdigest()


def _expected_worktree_binding(slot_value: Any) -> tuple[str, str]:
    """Derive trusted structural worktree identity from canonical slot authority.

    The path digest here binds the logical worktree locator to the canonical task/branch/slot
    identity. It is not a claim that a physical filesystem path exists. Physical path/process
    attestation remains reserved for the separately governed canary/runtime witness gate.
    """
    slot = _slot_mapping(slot_value)
    canonical_main_sha = _require_nonempty_string(slot.get("canonical_main_sha"), "slot canonical_main_sha")
    if not re.fullmatch(r"[0-9a-f]{40}", canonical_main_sha):
        raise SlotSelectionError("runtime_admission: slot canonical_main_sha must be a full lowercase commit SHA")
    worker_slot_id = _require_nonempty_string(slot.get("worker_slot_id"), "slot worker_slot_id")
    task_id = _require_nonempty_string(slot.get("task_id"), "slot task_id")
    execution_repository = _require_nonempty_string(slot.get("execution_repository"), "slot execution_repository")
    implementation_branch = _require_nonempty_string(slot.get("implementation_branch"), "slot implementation_branch")
    route_epoch = slot.get("route_epoch")
    if not isinstance(route_epoch, int) or isinstance(route_epoch, bool) or route_epoch < 1:
        raise SlotSelectionError("runtime_admission: slot route_epoch must be a positive integer")

    material = {
        "schema": WORKTREE_EXPECTATION_SCHEMA,
        "canonical_main_sha": canonical_main_sha,
        "execution_repository": execution_repository,
        "implementation_branch": implementation_branch,
        "task_id": task_id,
        "route_epoch": route_epoch,
        "worker_slot_id": worker_slot_id,
    }
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    worktree_id_digest = sha256(b"workbuddy-worktree-id-v1\x00" + payload).hexdigest()
    worktree_path_digest = sha256(b"workbuddy-worktree-path-v1\x00" + payload).hexdigest()
    return "WB-WORKTREE-" + worktree_id_digest[:24], worktree_path_digest


def _validate_acquired_resource_leases(
    raw_leases: Any, *, executor_id: str, worker_slot_id: str, run_id: str,
) -> tuple[str, ...]:
    if not isinstance(raw_leases, list):
        raise SlotSelectionError("runtime_admission: acquired_resource_leases must be a list")

    seen: set[str] = set()
    ids: list[str] = []
    for lease in raw_leases:
        if not isinstance(lease, Mapping):
            raise SlotSelectionError("runtime_admission: resource lease must be an object")
        lease_id = _require_nonempty_string(lease.get("resource_lease_id"), "resource_lease_id")
        if lease_id in seen:
            raise SlotSelectionError("runtime_admission: duplicate resource_lease_id")
        seen.add(lease_id)
        ids.append(lease_id)

        _require_nonempty_string(lease.get("resource_type"), "resource_type")
        if lease.get("holder_executor_id") != executor_id:
            raise SlotSelectionError("runtime_admission: cross-executor resource lease")
        if lease.get("worker_slot_id") != worker_slot_id:
            raise SlotSelectionError("runtime_admission: cross-slot resource lease")
        if lease.get("run_id") != run_id:
            raise SlotSelectionError("runtime_admission: cross-run resource lease")

        requested = lease.get("requested_quantity")
        granted = lease.get("granted_quantity")
        if not isinstance(requested, (int, float)) or isinstance(requested, bool) or requested < 0:
            raise SlotSelectionError("runtime_admission: invalid requested_quantity")
        if not isinstance(granted, (int, float)) or isinstance(granted, bool) or granted < 0:
            raise SlotSelectionError("runtime_admission: invalid granted_quantity")
        _require_nonempty_string(lease.get("unit"), "resource unit")

        generation = lease.get("generation")
        current_generation = lease.get("current_generation")
        if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
            raise SlotSelectionError("runtime_admission: invalid resource lease generation")
        if not isinstance(current_generation, int) or current_generation != generation:
            raise SlotSelectionError("runtime_admission: stale resource lease generation")
        if lease.get("lease_state") != "ACQUIRED":
            raise SlotSelectionError("runtime_admission: resource lease is not ACQUIRED")
        if lease.get("superseded") is not False:
            raise SlotSelectionError("runtime_admission: resource lease is superseded or unknown")
        _require_sha256_digest(lease.get("scheduler_admission_receipt_digest"), "scheduler admission receipt")
        _require_sha256_digest(lease.get("authority_graph_digest"), "authority graph digest")

        exclusive_or_mutable = lease.get("exclusive_or_mutable")
        if not isinstance(exclusive_or_mutable, bool):
            raise SlotSelectionError("runtime_admission: exclusive_or_mutable must be boolean")
        if exclusive_or_mutable:
            fencing = _require_nonempty_string(lease.get("fencing_token"), "fencing_token")
            current_fencing = _require_nonempty_string(lease.get("current_fencing_token"), "current_fencing_token")
            if fencing != current_fencing:
                raise SlotSelectionError("runtime_admission: stale resource fencing token")

    return tuple(sorted(ids))


def validate_runtime_binding(slot_value: Any, envelope: Mapping[str, Any]) -> RuntimeBindingResult:
    """Bind runtime identity/resource evidence without granting a physical process start."""
    slot = _slot_mapping(slot_value)
    if slot.get("logical_state") != "DECLARED":
        raise SlotSelectionError("runtime_admission: selected slot is not DECLARED")
    if not isinstance(envelope, Mapping):
        raise SlotSelectionError("runtime_admission: envelope must be an object")

    executor_id = _require_nonempty_string(envelope.get("executor_id"), "executor_id")
    run_id = _require_nonempty_string(envelope.get("run_id"), "run_id")
    worker_slot_id = _require_nonempty_string(envelope.get("worker_slot_id"), "worker_slot_id")
    if worker_slot_id != slot.get("worker_slot_id"):
        raise SlotSelectionError("runtime_admission: worker_slot_id mismatch")
    if envelope.get("canonical_main_sha") != slot.get("canonical_main_sha"):
        raise SlotSelectionError("runtime_admission: canonical_main_sha mismatch")
    if envelope.get("authority_chain_receipt_digest") != slot.get("authority_chain_receipt_digest"):
        raise SlotSelectionError("runtime_admission: authority-chain receipt mismatch")
    if envelope.get("writer_lease_identity") != slot.get("writer_lease_identity"):
        raise SlotSelectionError("runtime_admission: task writer-lease identity mismatch")

    expected_worktree_id, expected_worktree_path_digest = _expected_worktree_binding(slot)
    worktree_id = _require_nonempty_string(envelope.get("worktree_id"), "worktree_id")
    if worktree_id != expected_worktree_id:
        raise SlotSelectionError("runtime_admission: worktree_id mismatch")
    worktree_path_digest = _sha256_digest_hex(envelope.get("worktree_path_digest"), "worktree_path_digest")
    if worktree_path_digest != expected_worktree_path_digest:
        raise SlotSelectionError("runtime_admission: worktree_path_digest mismatch")

    lease_ids = _validate_acquired_resource_leases(
        envelope.get("acquired_resource_leases"),
        executor_id=executor_id,
        worker_slot_id=worker_slot_id,
        run_id=run_id,
    )

    ownership = envelope.get("process_ownership_receipt")
    process_ownership_status = "UNKNOWN_REQUIRING_PHYSICAL_CANARY"
    if ownership is not None:
        if not isinstance(ownership, Mapping):
            raise SlotSelectionError("runtime_admission: process_ownership_receipt must be an object")
        if ownership.get("executor_id") != executor_id or ownership.get("run_id") != run_id:
            raise SlotSelectionError("runtime_admission: process ownership identity mismatch")
        if ownership.get("worker_slot_id") != worker_slot_id:
            raise SlotSelectionError("runtime_admission: process ownership slot mismatch")
        root_pid = ownership.get("root_pid")
        if not isinstance(root_pid, int) or isinstance(root_pid, bool) or root_pid <= 0:
            raise SlotSelectionError("runtime_admission: invalid process ownership root_pid")
        _require_sha256_digest(ownership.get("process_tree_digest"), "process_tree_digest")
        if ownership.get("status") == "PROVEN":
            process_ownership_status = "STRUCTURALLY_PROVEN_RECEIPT_PRESENT"
        elif ownership.get("status") not in {"UNKNOWN", "NOT_TESTED"}:
            raise SlotSelectionError("runtime_admission: unsupported process ownership status")

    teardown = envelope.get("carrier_teardown_capability", "UNKNOWN")
    if teardown not in {"PROVEN", "UNKNOWN", "NOT_TESTED", "PARTIAL"}:
        raise SlotSelectionError("runtime_admission: invalid carrier teardown capability")

    blockers = ["SEPARATE_PHYSICAL_CANARY_GATE_REQUIRED"]
    if process_ownership_status != "STRUCTURALLY_PROVEN_RECEIPT_PRESENT":
        blockers.append("PROCESS_OWNERSHIP_NOT_PROVEN")
    if teardown != "PROVEN":
        blockers.append("CARRIER_TEARDOWN_CAPABILITY_NOT_PROVEN")
    if not lease_ids:
        blockers.append("NO_ACQUIRED_RESOURCE_LEASES_RECORDED")

    material = {
        "schema": RUNTIME_BINDING_SCHEMA,
        "canonical_main_sha": slot["canonical_main_sha"],
        "worker_slot_id": worker_slot_id,
        "task_id": slot["task_id"],
        "executor_id": executor_id,
        "run_id": run_id,
        "worktree_id": worktree_id,
        "worktree_path_digest": worktree_path_digest,
        "authority_chain_receipt_digest": slot["authority_chain_receipt_digest"],
        "writer_lease_identity": slot["writer_lease_identity"],
        "acquired_resource_lease_ids": list(lease_ids),
        "process_ownership_status": process_ownership_status,
        "carrier_teardown_capability": teardown,
        "process_start_authorized": False,
        "blockers": blockers,
    }
    return RuntimeBindingResult(
        schema=RUNTIME_BINDING_SCHEMA,
        status=PROCESS_START_BLOCKED,
        canonical_main_sha=str(slot["canonical_main_sha"]),
        worker_slot_id=worker_slot_id,
        task_id=str(slot["task_id"]),
        executor_id=executor_id,
        run_id=run_id,
        worktree_id=worktree_id,
        worktree_path_digest=worktree_path_digest,
        authority_chain_receipt_digest=str(slot["authority_chain_receipt_digest"]),
        writer_lease_identity=str(slot["writer_lease_identity"]),
        acquired_resource_lease_ids=lease_ids,
        process_ownership_status=process_ownership_status,
        carrier_teardown_capability=str(teardown),
        binding_digest=_canonical_json_digest(material),
        process_start_authorized=False,
        blockers=tuple(blockers),
    )


__all__ = [
    "SelectionResult", "RuntimeBindingResult", "SlotSelectionError",
    "select_workbuddy_slot", "validate_runtime_binding",
    "SELECTED", "AMBIGUOUS", "NO_ELIGIBLE", "NOT_FOUND", "CONFLICTING_SELECTOR",
    "PROCESS_START_BLOCKED",
]
