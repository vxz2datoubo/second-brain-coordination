from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

CANONICAL_REGISTRY_SCHEMA_VERSION = "1.5"
LEGACY_REGISTRY_SCHEMA_VERSIONS = frozenset({"1.0"})
SUPPORTED_REGISTRY_SCHEMA_VERSIONS = frozenset(
    {CANONICAL_REGISTRY_SCHEMA_VERSION, *LEGACY_REGISTRY_SCHEMA_VERSIONS}
)
EXPECTED_REGISTRY_ID = "ACTIVE-GPT-ENGINEERING-WORKERS-0001"
EXPECTED_AGENT_TYPE = "GPT_ENGINEERING_WORKER"
WORKER_REGISTRY_PATH = "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
PROGRAM_LANES_PATH = "coordination/ACTIVE-PROGRAM-LANES.yaml"

LIFECYCLE_RESERVED = "RESERVED_NON_EXECUTABLE"
LIFECYCLE_ACTIVE = "ACTIVE_EXECUTABLE"
LIFECYCLE_REVIEW_WAIT = "ENGINEERING_STOPPED_REVIEW_WAIT"
LIFECYCLE_ACCEPTED = "INDEPENDENTLY_ACCEPTED_AWAITING_CANONICALIZATION"
LIFECYCLE_CHANGES_REQUIRED = "CHANGES_REQUIRED_REMEDIATION_ELIGIBLE"
LIFECYCLE_CANONICAL_MERGED = "CANONICAL_MERGED_AWAITING_CLOSEOUT"
LIFECYCLE_RELEASED = "RELEASED_CLOSED"
LIFECYCLE_FROZEN = "FROZEN_SUPERSEDED"
LIFECYCLE_UNKNOWN = "UNKNOWN_FAIL_CLOSED"

KNOWN_LIFECYCLE_STATES = frozenset(
    {
        LIFECYCLE_RESERVED,
        LIFECYCLE_ACTIVE,
        LIFECYCLE_REVIEW_WAIT,
        LIFECYCLE_ACCEPTED,
        LIFECYCLE_CHANGES_REQUIRED,
        LIFECYCLE_CANONICAL_MERGED,
        LIFECYCLE_RELEASED,
        LIFECYCLE_FROZEN,
        LIFECYCLE_UNKNOWN,
    }
)

# Raw evidence supplied to this foundation resolver is advisory only.
# Independent review verdicts, canonical merges, closeout releases and
# supersession are governed authority facts. They must already be reflected in
# the canonical aggregate projection (or be verified by a later dedicated
# verifier) before they may change lifecycle truth.
_ADVISORY_EVENT_PRIORITY = {
    "PREWRITE_AUTHORIZATION": 10,
    "ROUTE_OR_LEASE_PROJECTION": 20,
    "ENGINEERING_STOP": 40,
}
_EXTERNAL_AUTHORITY_EVENT_KINDS = frozenset(
    {
        "CHANGES_REQUIRED",
        "INDEPENDENT_ACCEPT",
        "CANONICAL_MERGE",
        "CLOSEOUT_RELEASED",
        "FROZEN_SUPERSEDED",
    }
)
_KNOWN_EVENT_KINDS = frozenset({*_ADVISORY_EVENT_PRIORITY, *_EXTERNAL_AUTHORITY_EVENT_KINDS})
_REQUIRED_EVENT_IDENTITY_FIELDS = (
    "repository",
    "worker_slot_id",
    "task_id",
    "route_epoch",
    "issue",
    "pr",
    "exact_head",
)
_REVIEW_AUTHORITY_EVENT_KINDS = frozenset({"CHANGES_REQUIRED", "INDEPENDENT_ACCEPT"})
_REVIEW_PROVENANCE_FIELDS = ("review_ref", "review_result_ref")

# Canonical aggregate projection vocabulary is matched deliberately rather than
# by arbitrary substring. Unknown or negated strings such as NOT_RELEASED must
# never manufacture a stronger lifecycle state or free capacity.
_STATUS_REVIEW_WAIT = frozenset(
    {
        "ENGINEERING_STOPPED_WAITING_INDEPENDENT_REVIEW",
        "REVIEW_WAIT",
    }
)
_STATUS_ACCEPTED = frozenset(
    {
        "INDEPENDENTLY_ACCEPTED_AWAITING_SEPARATE_CANONICALIZATION",
        "INDEPENDENTLY_ACCEPTED_AWAITING_CANONICALIZATION",
    }
)
_STATUS_CANONICAL_MERGED = frozenset({"CANONICAL_MERGED_AWAITING_CLOSEOUT"})
_STATUS_CHANGES_REQUIRED = frozenset({"CHANGES_REQUIRED"})
_STATUS_RELEASED = frozenset(
    {
        "RELEASED",
        "WORKER_CLOSED",
        "CANONICAL_MERGED_WORKER_CLOSED",
    }
)
_CLOSURE_RELEASED = frozenset(
    {
        "RELEASED",
        "CANONICAL_MERGED_AND_WORKER_RELEASED",
    }
)
_STATUS_FROZEN_EXACT = frozenset({"FROZEN", "SUPERSEDED", "GOVERNANCE_INVALID"})
_STATUS_FROZEN_PREFIXES = ("FROZEN_", "SUPERSEDED_", "GOVERNANCE_INVALID_")
_STATUS_POSITIVE_CURRENT_EXECUTION = frozenset(
    {
        "ACTIVE",
        "ACTIVE_GOVERNED_EXECUTION",
        "ACTIVE_GOVERNED_PREWRITE",
    }
)


@dataclass(frozen=True)
class WorkerLifecycleResolution:
    schema_version: str
    lifecycle_state: str
    executable: bool
    occupies_capacity: bool
    terminal: bool
    current_write_authority: bool
    source_kind: str
    exact_head: str | None
    findings: tuple[str, ...]
    acceptance_authority: bool = False
    merge_authority: bool = False
    trade_authority: bool = False
    successor_release_authority: bool = False
    fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkerRegistryLifecycleAudit:
    schema_version: str | None
    registry_id: str | None
    agent_type: str | None
    slot_resolutions: tuple[dict[str, Any], ...]
    occupied_capacity_slots: tuple[str, ...]
    occupied_capacity_count: int | None
    configured_capacity_limit: int | None
    free_capacity_count: int | None
    capacity_state: str
    findings: tuple[str, ...]
    valid_for_observability: bool
    successor_release_authority: bool
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _fingerprint(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def registry_schema_findings(version: Any) -> tuple[str, ...]:
    if version == CANONICAL_REGISTRY_SCHEMA_VERSION:
        return ()
    if version in LEGACY_REGISTRY_SCHEMA_VERSIONS:
        return ("WORKER_REGISTRY_LEGACY_SCHEMA_COMPATIBILITY",)
    return ("WORKER_REGISTRY_SCHEMA_UNSUPPORTED_FAIL_CLOSED",)


def registry_schema_supported(version: Any) -> bool:
    return version in SUPPORTED_REGISTRY_SCHEMA_VERSIONS


def _matches_projection_status(
    value: Any,
    exact_values: Iterable[str],
    prefixes: Iterable[str] = (),
) -> bool:
    upper = str(value or "").upper()
    return upper in exact_values or any(upper.startswith(prefix) for prefix in prefixes)


def _terminal_projection_conflict_findings(slot: Mapping[str, Any]) -> tuple[str, ...]:
    activation = str(slot.get("activation_state") or "").upper()
    status = str(slot.get("status") or "").upper()
    findings: list[str] = []
    if activation == "ACTIVE":
        findings.append("TERMINAL_CONFLICTS_WITH_ACTIVE_ACTIVATION")
    if status in _STATUS_POSITIVE_CURRENT_EXECUTION:
        findings.append("TERMINAL_CONFLICTS_WITH_ACTIVE_STATUS")
    if slot.get("execution_allowed") is True:
        findings.append("TERMINAL_CONFLICTS_WITH_EXECUTION_ALLOWED")
    if findings:
        findings.append("CONTRADICTORY_TERMINAL_PROJECTION_FAILS_CLOSED")
    return tuple(findings)


def _state_semantics(state: str, execution_allowed: bool) -> tuple[bool, bool, bool, bool]:
    if state == LIFECYCLE_ACTIVE:
        executable = execution_allowed is True
        return executable, True, False, executable
    if state in {
        LIFECYCLE_RESERVED,
        LIFECYCLE_REVIEW_WAIT,
        LIFECYCLE_ACCEPTED,
        LIFECYCLE_CHANGES_REQUIRED,
        LIFECYCLE_CANONICAL_MERGED,
        LIFECYCLE_UNKNOWN,
    }:
        return False, True, state == LIFECYCLE_CHANGES_REQUIRED, False
    if state in {LIFECYCLE_RELEASED, LIFECYCLE_FROZEN}:
        return False, False, True, False
    return False, True, False, False


def _baseline_from_projection(slot: Mapping[str, Any]) -> tuple[str, list[str]]:
    activation = str(slot.get("activation_state") or "").upper()
    closure = str(slot.get("closure_state") or "").upper()
    status = str(slot.get("status") or "").upper()
    execution_allowed = slot.get("execution_allowed") is True
    findings: list[str] = []

    if closure == "RELEASED" or activation == "RELEASED":
        terminal_conflicts = _terminal_projection_conflict_findings(slot)
        if terminal_conflicts:
            findings.extend(terminal_conflicts)
            return LIFECYCLE_UNKNOWN, findings
        return LIFECYCLE_RELEASED, findings
    if activation == "FROZEN" or _matches_projection_status(
        status, _STATUS_FROZEN_EXACT, _STATUS_FROZEN_PREFIXES
    ):
        terminal_conflicts = _terminal_projection_conflict_findings(slot)
        if terminal_conflicts:
            findings.extend(terminal_conflicts)
            return LIFECYCLE_UNKNOWN, findings
        return LIFECYCLE_FROZEN, findings
    if activation == "CLOSED":
        if _matches_projection_status(status, _STATUS_RELEASED) or closure in _CLOSURE_RELEASED:
            terminal_conflicts = _terminal_projection_conflict_findings(slot)
            if terminal_conflicts:
                findings.extend(terminal_conflicts)
                return LIFECYCLE_UNKNOWN, findings
            return LIFECYCLE_RELEASED, findings
        findings.append("AMBIGUOUS_CLOSED_PROJECTION_FAILS_CLOSED")
        return LIFECYCLE_UNKNOWN, findings

    # Stronger canonical projections beat older REVIEW_WAIT prose, but only
    # when they match the governed vocabulary exactly. Text that merely embeds
    # one of these labels is not transition authority.
    if _matches_projection_status(status, _STATUS_ACCEPTED):
        if execution_allowed:
            findings.append("STALE_EXECUTION_FLAG_IGNORED_BY_ACCEPTED_STATE")
        return LIFECYCLE_ACCEPTED, findings
    if _matches_projection_status(status, _STATUS_CHANGES_REQUIRED):
        if execution_allowed:
            findings.append("STALE_EXECUTION_FLAG_IGNORED_BY_CHANGES_REQUIRED")
        return LIFECYCLE_CHANGES_REQUIRED, findings
    if _matches_projection_status(status, _STATUS_CANONICAL_MERGED):
        if execution_allowed:
            findings.append("STALE_EXECUTION_FLAG_IGNORED_BY_CANONICAL_MERGE")
        return LIFECYCLE_CANONICAL_MERGED, findings
    if activation == "REVIEW_WAIT" or _matches_projection_status(status, _STATUS_REVIEW_WAIT):
        if execution_allowed:
            findings.append("STALE_EXECUTION_FLAG_IGNORED_BY_REVIEW_WAIT")
        return LIFECYCLE_REVIEW_WAIT, findings

    if activation in {"RESERVED", "PREWRITE_RESERVED"}:
        if execution_allowed:
            findings.append("RESERVED_EXECUTION_FLAG_IGNORED")
        return LIFECYCLE_RESERVED, findings
    if activation == "ACTIVE":
        if not execution_allowed:
            findings.append("ACTIVE_WITHOUT_EXECUTION_FAILS_CLOSED")
            return LIFECYCLE_RESERVED, findings
        return LIFECYCLE_ACTIVE, findings

    resource_class = str(slot.get("resource_class") or "").upper()
    if resource_class == "REVIEW_WAIT_SLOT_OCCUPIED":
        findings.append("LIFECYCLE_RECOVERED_FROM_RESOURCE_CLASS")
        return LIFECYCLE_REVIEW_WAIT, findings
    if resource_class.startswith("RESERVED_") or status == "ACTIVE_GOVERNED_PREWRITE":
        findings.append("LIFECYCLE_RECOVERED_FROM_LEGACY_PROJECTION")
        return LIFECYCLE_RESERVED, findings

    findings.append("UNKNOWN_LIFECYCLE_FAIL_CLOSED")
    return LIFECYCLE_UNKNOWN, findings


def _event_identity_findings(slot: Mapping[str, Any], event: Mapping[str, Any]) -> tuple[str, ...]:
    findings: list[str] = []
    for field in _REQUIRED_EVENT_IDENTITY_FIELDS:
        expected = slot.get(field)
        actual = event.get(field)
        if expected is None or actual is None or str(expected) != str(actual):
            findings.append(f"LIFECYCLE_EVIDENCE_IDENTITY_INVALID:{field}")
    return tuple(findings)


def _review_provenance_findings(slot: Mapping[str, Any], event: Mapping[str, Any]) -> tuple[str, ...]:
    kind = str(event.get("kind") or "")
    if kind not in _REVIEW_AUTHORITY_EVENT_KINDS:
        return ()
    findings: list[str] = []
    for field in _REVIEW_PROVENANCE_FIELDS:
        expected = slot.get(field)
        actual = event.get(field)
        if expected is None or actual is None or str(expected) != str(actual):
            findings.append(f"LIFECYCLE_EVIDENCE_PROVENANCE_INVALID:{field}")
    return tuple(findings)


def _event_sort_key(event: Mapping[str, Any]) -> tuple[int, str, str]:
    kind = str(event.get("kind") or "")
    priority = _ADVISORY_EVENT_PRIORITY.get(kind, -1)
    observed_at = str(event.get("observed_at") or event.get("available_at") or "")
    return priority, observed_at, _canonical(dict(event))


def _advisory_state_from_event(kind: str, event: Mapping[str, Any]) -> str | None:
    if kind == "ENGINEERING_STOP":
        return LIFECYCLE_REVIEW_WAIT
    if kind in {"PREWRITE_AUTHORIZATION", "ROUTE_OR_LEASE_PROJECTION"}:
        return LIFECYCLE_ACTIVE if event.get("execution_allowed") is True else LIFECYCLE_RESERVED
    return None


def _can_apply_advisory_transition(
    baseline_state: str,
    proposed_state: str,
    execution_allowed: bool,
) -> bool:
    baseline_exec, baseline_occupies, baseline_terminal, _ = _state_semantics(
        baseline_state, execution_allowed
    )
    proposed_exec, proposed_occupies, proposed_terminal, _ = _state_semantics(
        proposed_state, execution_allowed
    )
    if proposed_exec and not baseline_exec:
        return False
    if baseline_occupies and not proposed_occupies:
        return False
    if baseline_terminal and not proposed_terminal:
        return False
    return True


def resolve_worker_lifecycle(
    slot: Mapping[str, Any],
    evidence_events: Sequence[Mapping[str, Any]] = (),
) -> WorkerLifecycleResolution:
    baseline_state, findings = _baseline_from_projection(slot)
    state = baseline_state
    source_kind = "CANONICAL_AGGREGATE_PROJECTION"
    execution_allowed = slot.get("execution_allowed") is True

    advisory_events: list[Mapping[str, Any]] = []
    for event in evidence_events:
        kind = str(event.get("kind") or "")
        if kind not in _KNOWN_EVENT_KINDS:
            findings.append("UNKNOWN_LIFECYCLE_EVIDENCE_KIND_IGNORED")
            continue

        identity_findings = _event_identity_findings(slot, event)
        if identity_findings:
            findings.extend(identity_findings)
            findings.append("INCOMPLETE_OR_FOREIGN_LIFECYCLE_EVIDENCE_IGNORED")
            continue

        provenance_findings = _review_provenance_findings(slot, event)
        if provenance_findings:
            findings.extend(provenance_findings)
            findings.append("UNVERIFIED_OR_FOREIGN_REVIEW_EVIDENCE_IGNORED")
            continue

        if kind in _EXTERNAL_AUTHORITY_EVENT_KINDS:
            findings.append(f"EXTERNAL_AUTHORITY_EVENT_REQUIRES_GOVERNED_PROJECTION:{kind}")
            continue

        advisory_events.append(event)

    if advisory_events:
        strongest = max(advisory_events, key=_event_sort_key)
        kind = str(strongest.get("kind") or "")
        proposed_state = _advisory_state_from_event(kind, strongest)
        if proposed_state is None:
            findings.append("UNRESOLVED_LIFECYCLE_EVIDENCE_FAIL_CLOSED")
        elif _can_apply_advisory_transition(baseline_state, proposed_state, execution_allowed):
            state = proposed_state
            source_kind = f"ADVISORY_{kind}"
            if state != LIFECYCLE_ACTIVE and execution_allowed:
                findings.append("STALE_EXECUTION_FLAG_IGNORED_BY_STRONGER_EVIDENCE")
        else:
            findings.append("ADVISORY_EVENT_AUTHORITY_ESCALATION_BLOCKED")

    executable, occupies_capacity, terminal, current_write_authority = _state_semantics(
        state, execution_allowed
    )
    if state == LIFECYCLE_ACTIVE and not execution_allowed:
        executable = False
        current_write_authority = False
        findings.append("ACTIVE_EXECUTION_PREREQUISITE_MISSING")

    exact_head = slot.get("exact_head")
    payload = {
        "schema_version": "WorkerLifecycleResolution/v1",
        "lifecycle_state": state,
        "executable": executable,
        "occupies_capacity": occupies_capacity,
        "terminal": terminal,
        "current_write_authority": current_write_authority,
        "source_kind": source_kind,
        "exact_head": str(exact_head) if exact_head is not None else None,
        "findings": sorted(set(findings)),
        "acceptance_authority": False,
        "merge_authority": False,
        "trade_authority": False,
        "successor_release_authority": False,
    }
    return WorkerLifecycleResolution(
        schema_version=payload["schema_version"],
        lifecycle_state=state,
        executable=executable,
        occupies_capacity=occupies_capacity,
        terminal=terminal,
        current_write_authority=current_write_authority,
        source_kind=source_kind,
        exact_head=payload["exact_head"],
        findings=tuple(payload["findings"]),
        acceptance_authority=False,
        merge_authority=False,
        trade_authority=False,
        successor_release_authority=False,
        fingerprint=_fingerprint(payload),
    )


def occupied_capacity_count(
    slots: Sequence[Mapping[str, Any]],
    evidence_by_slot: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> int:
    evidence_by_slot = evidence_by_slot or {}
    count = 0
    for slot in slots:
        slot_id = str(slot.get("worker_slot_id") or "")
        resolution = resolve_worker_lifecycle(slot, evidence_by_slot.get(slot_id, ()))
        if resolution.occupies_capacity:
            count += 1
    return count


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected mapping: {path}")
    return payload


def _capacity_limit_from_program(path: Path) -> tuple[int | None, list[str]]:
    try:
        program = _load_yaml_mapping(path)
    except (OSError, ValueError, TypeError, yaml.YAMLError):
        return None, ["PROGRAM_LANES_CAPACITY_UNREADABLE"]
    policy = program.get("portfolio_capacity_policy")
    candidate = policy.get("gpt_engineering_worker_active_slots_max") if isinstance(policy, dict) else None
    if isinstance(candidate, int) and not isinstance(candidate, bool) and candidate >= 1:
        return candidate, []
    return None, ["GPT_WORKER_CAPACITY_LIMIT_UNKNOWN"]


def _failed_audit(
    capacity_limit: int | None,
    findings: Sequence[str],
) -> WorkerRegistryLifecycleAudit:
    payload = {
        "schema_version": None,
        "registry_id": None,
        "agent_type": None,
        "slot_resolutions": [],
        "occupied_capacity_slots": [],
        "occupied_capacity_count": None,
        "configured_capacity_limit": capacity_limit,
        "free_capacity_count": None,
        "capacity_state": "UNKNOWN_FAIL_CLOSED",
        "findings": sorted(set(findings)),
        "valid_for_observability": False,
        "successor_release_authority": False,
    }
    return WorkerRegistryLifecycleAudit(
        schema_version=None,
        registry_id=None,
        agent_type=None,
        slot_resolutions=(),
        occupied_capacity_slots=(),
        occupied_capacity_count=None,
        configured_capacity_limit=capacity_limit,
        free_capacity_count=None,
        capacity_state="UNKNOWN_FAIL_CLOSED",
        findings=tuple(payload["findings"]),
        valid_for_observability=False,
        successor_release_authority=False,
        fingerprint=_fingerprint(payload),
    )


def audit_worker_registry_lifecycle(repo_root: Path) -> WorkerRegistryLifecycleAudit:
    root = repo_root.resolve()
    findings: list[str] = []
    registry_path = root / WORKER_REGISTRY_PATH
    program_path = root / PROGRAM_LANES_PATH
    capacity_limit, capacity_findings = _capacity_limit_from_program(program_path)
    findings.extend(capacity_findings)

    try:
        registry = _load_yaml_mapping(registry_path)
    except (OSError, ValueError, TypeError, yaml.YAMLError):
        findings.append("WORKER_REGISTRY_UNREADABLE_FAIL_CLOSED")
        return _failed_audit(capacity_limit, findings)

    version = registry.get("schema_version")
    findings.extend(registry_schema_findings(version))
    if registry.get("registry_id") != EXPECTED_REGISTRY_ID:
        findings.append("WORKER_REGISTRY_ID_INVALID")
    if registry.get("agent_type") != EXPECTED_AGENT_TYPE:
        findings.append("WORKER_REGISTRY_AGENT_TYPE_INVALID")

    raw_slots = registry.get("worker_slots")
    if not isinstance(raw_slots, list):
        findings.append("WORKER_REGISTRY_SLOTS_NOT_LIST_FAIL_CLOSED")
        return _failed_audit(capacity_limit, findings)

    slot_resolutions: list[dict[str, Any]] = []
    occupied: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_slots):
        if not isinstance(raw, dict):
            findings.append(f"WORKER_SLOT_NOT_MAPPING:{index}")
            continue
        slot_id = str(raw.get("worker_slot_id") or "")
        if not slot_id:
            findings.append(f"WORKER_SLOT_ID_MISSING:{index}")
            slot_id = f"UNKNOWN:{index}"
        if slot_id in seen:
            findings.append(f"WORKER_SLOT_ID_DUPLICATE:{slot_id}")
        seen.add(slot_id)
        resolution = resolve_worker_lifecycle(raw)
        slot_resolutions.append({"worker_slot_id": slot_id, **resolution.to_dict()})
        if resolution.occupies_capacity:
            occupied.append(slot_id)
        if resolution.lifecycle_state == LIFECYCLE_UNKNOWN:
            findings.append(f"WORKER_SLOT_LIFECYCLE_UNKNOWN:{slot_id}")

    if capacity_limit is not None and len(occupied) > capacity_limit:
        findings.append("GPT_WORKER_OCCUPIED_CAPACITY_EXCEEDED")

    error_findings = [
        item for item in findings if item != "WORKER_REGISTRY_LEGACY_SCHEMA_COMPATIBILITY"
    ]
    valid = not error_findings
    free_capacity = (
        max(0, capacity_limit - len(occupied))
        if valid and capacity_limit is not None
        else None
    )
    capacity_state = "KNOWN_OBSERVATION" if valid and capacity_limit is not None else "UNKNOWN_FAIL_CLOSED"
    payload = {
        "schema_version": str(version) if version is not None else None,
        "registry_id": registry.get("registry_id"),
        "agent_type": registry.get("agent_type"),
        "slot_resolutions": slot_resolutions,
        "occupied_capacity_slots": occupied,
        "occupied_capacity_count": len(occupied),
        "configured_capacity_limit": capacity_limit,
        "free_capacity_count": free_capacity,
        "capacity_state": capacity_state,
        "findings": sorted(set(findings)),
        "valid_for_observability": valid,
        "successor_release_authority": False,
    }
    return WorkerRegistryLifecycleAudit(
        schema_version=payload["schema_version"],
        registry_id=payload["registry_id"],
        agent_type=payload["agent_type"],
        slot_resolutions=tuple(slot_resolutions),
        occupied_capacity_slots=tuple(occupied),
        occupied_capacity_count=len(occupied),
        configured_capacity_limit=capacity_limit,
        free_capacity_count=free_capacity,
        capacity_state=capacity_state,
        findings=tuple(payload["findings"]),
        valid_for_observability=valid,
        successor_release_authority=False,
        fingerprint=_fingerprint(payload),
    )