from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence

CANONICAL_REGISTRY_SCHEMA_VERSION = "1.5"
LEGACY_REGISTRY_SCHEMA_VERSIONS = frozenset({"1.0"})
SUPPORTED_REGISTRY_SCHEMA_VERSIONS = frozenset(
    {CANONICAL_REGISTRY_SCHEMA_VERSION, *LEGACY_REGISTRY_SCHEMA_VERSIONS}
)

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

# Evidence is deliberately ordered by authority, not by caller list order.
# A matching exact-head terminal result outranks stale route/lease projection.
_EVIDENCE_PRIORITY = {
    "PREWRITE_AUTHORIZATION": 10,
    "ROUTE_OR_LEASE_PROJECTION": 20,
    "ENGINEERING_STOP": 40,
    "CHANGES_REQUIRED": 50,
    "INDEPENDENT_ACCEPT": 60,
    "CANONICAL_MERGE": 70,
    "CLOSEOUT_RELEASED": 80,
    "FROZEN_SUPERSEDED": 80,
}

_STATUS_REVIEW_WAIT = (
    "ENGINEERING_STOPPED_WAITING_INDEPENDENT_REVIEW",
    "REVIEW_WAIT",
)
_STATUS_ACCEPTED = (
    "INDEPENDENTLY_ACCEPTED_AWAITING_SEPARATE_CANONICALIZATION",
    "INDEPENDENTLY_ACCEPTED_AWAITING_CANONICALIZATION",
)
_STATUS_CANONICAL_MERGED = (
    "CANONICAL_MERGED_AWAITING_CLOSEOUT",
    "CANONICAL_MERGED_WORKER_CLOSED",
)
_STATUS_FROZEN = ("FROZEN", "SUPERSEDED", "GOVERNANCE_INVALID")
_STATUS_RELEASED = ("RELEASED", "WORKER_CLOSED")
_STATUS_CHANGES_REQUIRED = ("CHANGES_REQUIRED",)


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
    fingerprint: str = ""

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


def _contains_any(value: Any, tokens: Iterable[str]) -> bool:
    upper = str(value or "").upper()
    return any(token in upper for token in tokens)


def _state_semantics(state: str, execution_allowed: bool) -> tuple[bool, bool, bool, bool]:
    """Return executable, occupies_capacity, terminal, current_write_authority."""

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
        # UNKNOWN occupies capacity to fail closed: ambiguity can never create a free slot.
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

    # Explicit terminal closure is stronger than an older presentation status.
    if closure == "RELEASED" or activation == "RELEASED":
        return LIFECYCLE_RELEASED, findings
    if activation in {"FROZEN"} or _contains_any(status, _STATUS_FROZEN):
        return LIFECYCLE_FROZEN, findings
    if activation in {"CLOSED"}:
        if _contains_any(status, _STATUS_CANONICAL_MERGED + _STATUS_RELEASED):
            return LIFECYCLE_RELEASED, findings
        findings.append("LEGACY_CLOSED_NORMALIZED_TO_RELEASED_CLOSED")
        return LIFECYCLE_RELEASED, findings

    # Newer human/projection states override stale ACTIVE/PREWRITE booleans.
    if activation == "REVIEW_WAIT" or _contains_any(status, _STATUS_REVIEW_WAIT):
        if execution_allowed:
            findings.append("STALE_EXECUTION_FLAG_IGNORED_BY_REVIEW_WAIT")
        return LIFECYCLE_REVIEW_WAIT, findings
    if _contains_any(status, _STATUS_ACCEPTED):
        if execution_allowed:
            findings.append("STALE_EXECUTION_FLAG_IGNORED_BY_ACCEPTED_STATE")
        return LIFECYCLE_ACCEPTED, findings
    if _contains_any(status, _STATUS_CHANGES_REQUIRED):
        if execution_allowed:
            findings.append("STALE_EXECUTION_FLAG_IGNORED_BY_CHANGES_REQUIRED")
        return LIFECYCLE_CHANGES_REQUIRED, findings
    if _contains_any(status, ("CANONICAL_MERGED_AWAITING_CLOSEOUT",)):
        if execution_allowed:
            findings.append("STALE_EXECUTION_FLAG_IGNORED_BY_CANONICAL_MERGE")
        return LIFECYCLE_CANONICAL_MERGED, findings

    if activation in {"RESERVED", "PREWRITE_RESERVED"}:
        if execution_allowed:
            findings.append("RESERVED_EXECUTION_FLAG_IGNORED")
        return LIFECYCLE_RESERVED, findings
    if activation == "ACTIVE":
        if not execution_allowed:
            findings.append("ACTIVE_WITHOUT_EXECUTION_FAILS_CLOSED")
            return LIFECYCLE_RESERVED, findings
        return LIFECYCLE_ACTIVE, findings

    # Some pre-R6 projections used only status/resource class for reservation.
    resource_class = str(slot.get("resource_class") or "").upper()
    if "REVIEW_WAIT_SLOT_OCCUPIED" in resource_class:
        findings.append("LIFECYCLE_RECOVERED_FROM_RESOURCE_CLASS")
        return LIFECYCLE_REVIEW_WAIT, findings
    if "RESERV" in resource_class or "PREWRITE" in status:
        findings.append("LIFECYCLE_RECOVERED_FROM_LEGACY_PROJECTION")
        return LIFECYCLE_RESERVED, findings

    findings.append("UNKNOWN_LIFECYCLE_FAIL_CLOSED")
    return LIFECYCLE_UNKNOWN, findings


def _event_identity_matches(slot: Mapping[str, Any], event: Mapping[str, Any]) -> bool:
    event_head = event.get("exact_head")
    slot_head = slot.get("exact_head")
    if event_head is not None and slot_head is not None and str(event_head) != str(slot_head):
        return False
    for field in ("worker_slot_id", "task_id", "issue", "pr", "route_epoch"):
        expected = slot.get(field)
        actual = event.get(field)
        if actual is not None and expected is not None and str(actual) != str(expected):
            return False
    return True


def _event_sort_key(event: Mapping[str, Any]) -> tuple[int, str, str]:
    kind = str(event.get("kind") or "")
    priority = _EVIDENCE_PRIORITY.get(kind, -1)
    observed_at = str(event.get("observed_at") or event.get("available_at") or "")
    return priority, observed_at, _canonical(dict(event))


def _state_from_event(kind: str, event: Mapping[str, Any]) -> str | None:
    if kind == "CLOSEOUT_RELEASED":
        return LIFECYCLE_RELEASED
    if kind == "FROZEN_SUPERSEDED":
        return LIFECYCLE_FROZEN
    if kind == "CANONICAL_MERGE":
        return LIFECYCLE_CANONICAL_MERGED
    if kind == "INDEPENDENT_ACCEPT":
        return LIFECYCLE_ACCEPTED
    if kind == "CHANGES_REQUIRED":
        return LIFECYCLE_CHANGES_REQUIRED
    if kind == "ENGINEERING_STOP":
        return LIFECYCLE_REVIEW_WAIT
    if kind == "PREWRITE_AUTHORIZATION":
        return LIFECYCLE_ACTIVE if event.get("execution_allowed") is True else LIFECYCLE_RESERVED
    if kind == "ROUTE_OR_LEASE_PROJECTION":
        return LIFECYCLE_ACTIVE if event.get("execution_allowed") is True else LIFECYCLE_RESERVED
    return None


def resolve_worker_lifecycle(
    slot: Mapping[str, Any],
    evidence_events: Sequence[Mapping[str, Any]] = (),
) -> WorkerLifecycleResolution:
    """Resolve one worker lifecycle deterministically and fail closed.

    Aggregate slot fields are a projection. Optional evidence events are stronger facts gathered
    by callers from exact-head handoff/review/merge/closeout artifacts. Events with mismatching
    exact-head/task/Issue/PR/epoch identity are retained only as findings and never mutate state.
    """

    state, findings = _baseline_from_projection(slot)
    source_kind = "AGGREGATE_PROJECTION"

    matching_events: list[Mapping[str, Any]] = []
    for event in evidence_events:
        kind = str(event.get("kind") or "")
        if kind not in _EVIDENCE_PRIORITY:
            findings.append("UNKNOWN_LIFECYCLE_EVIDENCE_KIND_IGNORED")
            continue
        if not _event_identity_matches(slot, event):
            findings.append("STALE_OR_FOREIGN_LIFECYCLE_EVIDENCE_IGNORED")
            continue
        matching_events.append(event)

    if matching_events:
        strongest = max(matching_events, key=_event_sort_key)
        kind = str(strongest.get("kind") or "")
        event_state = _state_from_event(kind, strongest)
        if event_state is None:
            findings.append("UNRESOLVED_LIFECYCLE_EVIDENCE_FAIL_CLOSED")
            state = LIFECYCLE_UNKNOWN
            source_kind = kind or "UNKNOWN_EVIDENCE"
        else:
            state = event_state
            source_kind = kind
            if state != LIFECYCLE_ACTIVE and slot.get("execution_allowed") is True:
                findings.append("STALE_EXECUTION_FLAG_IGNORED_BY_STRONGER_EVIDENCE")

    execution_allowed = slot.get("execution_allowed") is True
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
    }
    fingerprint = _fingerprint(payload)
    return WorkerLifecycleResolution(
        schema_version="WorkerLifecycleResolution/v1",
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
        fingerprint=fingerprint,
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
