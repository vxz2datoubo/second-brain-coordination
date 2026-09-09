"""WorkBuddy-specific plural slot projection over the canonical unified task registry.

This module is intentionally not a scheduler and not an authority registry. It consumes
one protected exact-SHA snapshot of the existing Unified Execution Fabric (UEF) registry,
projects registered WORKBUDDY task authorities into deterministic logical slot identities,
and preserves the legacy singular task file only as a compatibility default.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from coordination.EXECUTION import unified_active_task_registry as registry

ExecutionContractError = registry.ExecutionContractError

SLOT_SCHEMA = "WORKBUDDY_EXECUTOR_SLOT_PROJECTION/v1"
PROJECTION_SCHEMA = "WORKBUDDY_EXECUTOR_SLOT_SET/v1"
TARGET_AGENT = "WORKBUDDY"
SLOT_STATE_DECLARED = "DECLARED"
SLOT_STATE_BLOCKED = "BLOCKED"
PROCESS_START_STATUS = "NOT_AUTHORIZED_BY_SLOT_PROJECTION"
UNKNOWN_RUNTIME_EVIDENCE = "UNKNOWN_REQUIRING_PHYSICAL_CANARY"


class WorkBuddySlotError(ExecutionContractError):
    """Fail-closed slot projection/selection error."""


@dataclass(frozen=True)
class WorkBuddySlot:
    schema: str
    canonical_main_sha: str
    active_task_index_ref: str
    legacy_default: bool
    worker_slot_id: str
    project_id: str
    task_id: str
    route_epoch: int
    execution_repository: str
    implementation_branch: str
    exact_base_sha: str
    collision_domain: str
    authority_chain_receipt_digest: str
    writer_lease_identity: str
    authorized_paths: tuple[str, ...]
    completion_signal: str | None
    logical_state: str
    declared_execution_allowed: bool
    declared_active: bool
    declared_blocked_by: str | None
    process_start_status: str
    worktree_identity_state: str
    process_ownership_state: str
    carrier_teardown_capability: str

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["authorized_paths"] = list(self.authorized_paths)
        return value


@dataclass(frozen=True)
class WorkBuddySlotSet:
    schema: str
    canonical_main_sha: str
    registry_ref: str
    registry_digest: str
    legacy_default_ref: str
    slots: tuple[WorkBuddySlot, ...]
    process_start_authorized: bool
    physical_parallelism_proven: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "canonical_main_sha": self.canonical_main_sha,
            "registry_ref": self.registry_ref,
            "registry_digest": self.registry_digest,
            "legacy_default_ref": self.legacy_default_ref,
            "slots": [slot.as_dict() for slot in self.slots],
            "process_start_authorized": self.process_start_authorized,
            "physical_parallelism_proven": self.physical_parallelism_proven,
        }


def _sha256_hex(data: bytes) -> str:
    return sha256(data).hexdigest()


def _stable_worker_slot_id(authority: Mapping[str, Any]) -> str:
    """Derive stable logical slot identity only from trusted canonical task identity."""
    material = {
        "control_plane_repository": authority["control_plane_repository"],
        "execution_repository": authority["execution_repository"],
        "project_id": authority["project_id"],
        "task_id": authority["task_id"],
        "route_epoch": authority["route_epoch"],
    }
    digest = sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return "WB-SLOT-" + digest[:24]


def _parse_registry_metadata(raw: bytes) -> tuple[tuple[str, bool], ...]:
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=registry._unique_object)
    except ExecutionContractError:
        raise
    except Exception as exc:
        raise WorkBuddySlotError("workbuddy_slots: registry is not duplicate-safe JSON") from exc

    if not isinstance(data, Mapping):
        raise WorkBuddySlotError("workbuddy_slots: registry root must be an object")
    if data.get("schema") != registry.REGISTRY_SCHEMA:
        raise WorkBuddySlotError("workbuddy_slots: wrong registry schema")
    if data.get("control_plane_repository") != registry.base.TRUSTED_CONTROL_PLANE_REPOSITORY:
        raise WorkBuddySlotError("workbuddy_slots: wrong control-plane repository")
    if data.get("registry_status") != "ACTIVE":
        raise WorkBuddySlotError("workbuddy_slots: registry is not ACTIVE")

    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise WorkBuddySlotError("workbuddy_slots: registry entries must be non-empty")

    parsed: list[tuple[str, bool]] = []
    legacy_count = 0
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise WorkBuddySlotError("workbuddy_slots: registry entry must be an object")
        if entry.get("status") != "REGISTERED":
            raise WorkBuddySlotError("workbuddy_slots: unregistered entry is not admissible")
        ref = entry.get("active_task_index_ref")
        if not isinstance(ref, str) or not ref:
            raise WorkBuddySlotError("workbuddy_slots: missing task-index ref")
        registry.base._validate_ref(ref)
        if not ref.startswith("coordination/"):
            raise WorkBuddySlotError("workbuddy_slots: task-index ref escaped coordination trust root")
        legacy = entry.get("legacy_default") is True
        if legacy:
            legacy_count += 1
            if ref != registry.LEGACY_DEFAULT_REF:
                raise WorkBuddySlotError("workbuddy_slots: legacy_default points at non-legacy index")
        parsed.append((ref, legacy))

    refs = [ref for ref, _ in parsed]
    if len(refs) != len(set(refs)):
        raise WorkBuddySlotError("workbuddy_slots: duplicate task-index ref")
    if legacy_count != 1 or registry.LEGACY_DEFAULT_REF not in refs:
        raise WorkBuddySlotError("workbuddy_slots: canonical legacy default must remain registered exactly once")
    return tuple(parsed)


def _cached_exact_sha_reader(read: Callable[[str], bytes]) -> tuple[Callable[[str], bytes], dict[str, bytes]]:
    """Cache first Git-object bytes per path for this frozen validation snapshot."""
    cache: dict[str, bytes] = {}

    def cached(path: str) -> bytes:
        registry.base._validate_ref(path)
        if path not in cache:
            value = read(path)
            if not isinstance(value, (bytes, bytearray)):
                raise WorkBuddySlotError("workbuddy_slots: protected authority reader returned non-bytes")
            cache[path] = bytes(value)
        return cache[path]

    return cached, cache


def _validate_authority_set(
    authorities: Sequence[registry.base.VerifiedCanonicalAuthority], canonical_main_sha: str
) -> None:
    mappings = [authority.as_mapping() for authority in authorities]
    seen_task: set[tuple[str, int]] = set()
    seen_collision: set[tuple[str, str]] = set()
    seen_branch: set[tuple[str, str]] = set()

    for current in mappings:
        if current.get("canonical_main_sha") != canonical_main_sha:
            raise WorkBuddySlotError("workbuddy_slots: authority escaped frozen canonical-main snapshot")
        task_identity = (str(current["task_id"]), int(current["route_epoch"]))
        if task_identity in seen_task:
            raise WorkBuddySlotError("workbuddy_slots: duplicate task identity")
        seen_task.add(task_identity)

        repo = str(current["execution_repository"])
        collision = (repo, str(current["collision_domain"]))
        if collision in seen_collision:
            raise WorkBuddySlotError("workbuddy_slots: active authorities share collision domain")
        seen_collision.add(collision)

        branch = (repo, str(current["implementation_branch"]))
        if branch in seen_branch:
            raise WorkBuddySlotError("workbuddy_slots: active authorities share implementation branch")
        seen_branch.add(branch)

    for index, left in enumerate(mappings):
        for right in mappings[index + 1 :]:
            if registry._authority_write_surfaces_overlap(left, right):
                raise WorkBuddySlotError("workbuddy_slots: active authority write surfaces overlap or are ambiguous")


def _project_slot(
    *, canonical_main_sha: str, active_task_index_ref: str, active_text: str,
    legacy_default: bool, authority: registry.base.VerifiedCanonicalAuthority,
) -> WorkBuddySlot | None:
    target_agent = registry.base._scalar(active_text, "target_agent", required=False)
    if target_agent != TARGET_AGENT:
        return None

    mapping = authority.as_mapping()
    registry.base.validate_canonical_authority(authority)

    status = registry.base._scalar(active_text, "status", required=False)
    declared_execution_allowed = registry.base._scalar(active_text, "execution_allowed", required=False)
    declared_active = registry.base._scalar(active_text, "active", required=False)
    blocked_by = registry.base._scalar(active_text, "blocked_by", required=False)
    completion_signal = registry.base._scalar(active_text, "completion_signal", required=False)

    if not isinstance(declared_execution_allowed, bool):
        raise WorkBuddySlotError(f"workbuddy_slots: {active_task_index_ref} has malformed execution_allowed")
    if not isinstance(declared_active, bool):
        raise WorkBuddySlotError(f"workbuddy_slots: {active_task_index_ref} has malformed active")

    logical_state = SLOT_STATE_DECLARED if (
        status == "READY" and declared_execution_allowed and declared_active and blocked_by is None
    ) else SLOT_STATE_BLOCKED

    paths = mapping.get("authorized_paths")
    if not isinstance(paths, (list, tuple)):
        raise WorkBuddySlotError("workbuddy_slots: malformed authorized_paths")
    canonical_paths = tuple(registry._canonicalize_authorized_paths(paths))

    receipt = mapping.get("authority_chain_receipt_digest")
    writer_lease_identity = mapping.get("writer_lease_identity")
    if not isinstance(receipt, str) or not receipt.startswith("sha256:"):
        raise WorkBuddySlotError("workbuddy_slots: missing canonical authority-chain receipt digest")
    if not isinstance(writer_lease_identity, str) or not writer_lease_identity:
        raise WorkBuddySlotError("workbuddy_slots: missing canonical writer-lease identity")

    return WorkBuddySlot(
        schema=SLOT_SCHEMA,
        canonical_main_sha=canonical_main_sha,
        active_task_index_ref=active_task_index_ref,
        legacy_default=legacy_default,
        worker_slot_id=_stable_worker_slot_id(mapping),
        project_id=str(mapping["project_id"]),
        task_id=str(mapping["task_id"]),
        route_epoch=int(mapping["route_epoch"]),
        execution_repository=str(mapping["execution_repository"]),
        implementation_branch=str(mapping["implementation_branch"]),
        exact_base_sha=str(mapping["exact_base_sha"]),
        collision_domain=str(mapping["collision_domain"]),
        authority_chain_receipt_digest=receipt,
        writer_lease_identity=writer_lease_identity,
        authorized_paths=canonical_paths,
        completion_signal=str(completion_signal) if completion_signal is not None else None,
        logical_state=logical_state,
        declared_execution_allowed=declared_execution_allowed,
        declared_active=declared_active,
        declared_blocked_by=str(blocked_by) if blocked_by is not None else None,
        process_start_status=PROCESS_START_STATUS,
        worktree_identity_state="UNBOUND_UNTIL_RUNTIME_ADMISSION",
        process_ownership_state=UNKNOWN_RUNTIME_EVIDENCE,
        carrier_teardown_capability=UNKNOWN_RUNTIME_EVIDENCE,
    )


def build_slot_set_from_frozen_snapshot(
    *, canonical_main_sha: str, registry_raw: bytes, read: Callable[[str], bytes],
    repo_path: str | Path = ".", revalidate_project_adapters: bool = True,
) -> WorkBuddySlotSet:
    metadata = _parse_registry_metadata(registry_raw)
    expected_refs = registry._parse_registry(registry_raw)
    if tuple(ref for ref, _ in metadata) != expected_refs:
        raise WorkBuddySlotError("workbuddy_slots: registry metadata and canonical parser disagree")

    cached_read, _cache = _cached_exact_sha_reader(read)
    authorities: list[registry.base.VerifiedCanonicalAuthority] = []
    docs: dict[str, str] = {}

    for ref, _legacy in metadata:
        active_text = cached_read(ref).decode("utf-8")
        docs[ref] = active_text
        authority = registry._build_authority_from_open(canonical_main_sha, cached_read, ref)
        registry.base.validate_canonical_authority(authority)
        if revalidate_project_adapters:
            registry.gate._revalidate_project_adapter_at_sha(repo_path, authority.as_mapping())
        authorities.append(authority)

    _validate_authority_set(authorities, canonical_main_sha)

    slots: list[WorkBuddySlot] = []
    seen_slot_ids: set[str] = set()
    for (ref, legacy), authority in zip(metadata, authorities):
        slot = _project_slot(
            canonical_main_sha=canonical_main_sha,
            active_task_index_ref=ref,
            active_text=docs[ref],
            legacy_default=legacy,
            authority=authority,
        )
        if slot is None:
            continue
        if slot.worker_slot_id in seen_slot_ids:
            raise WorkBuddySlotError("workbuddy_slots: duplicate worker_slot_id")
        seen_slot_ids.add(slot.worker_slot_id)
        slots.append(slot)

    if not slots:
        raise WorkBuddySlotError("workbuddy_slots: no registered WORKBUDDY slots")
    slots.sort(key=lambda item: (item.route_epoch, item.task_id, item.worker_slot_id))

    return WorkBuddySlotSet(
        schema=PROJECTION_SCHEMA,
        canonical_main_sha=canonical_main_sha,
        registry_ref=registry.REGISTRY_REF,
        registry_digest="sha256:" + _sha256_hex(registry_raw),
        legacy_default_ref=registry.LEGACY_DEFAULT_REF,
        slots=tuple(slots),
        process_start_authorized=False,
        physical_parallelism_proven=False,
    )


def load_workbuddy_slot_set(repo_path: str | Path = ".") -> WorkBuddySlotSet:
    observed_main, protected_read = registry.gate._protected_open(repo_path)
    cached_read, _cache = _cached_exact_sha_reader(protected_read)
    registry_raw = cached_read(registry.REGISTRY_REF)
    slot_set = build_slot_set_from_frozen_snapshot(
        canonical_main_sha=observed_main,
        registry_raw=registry_raw,
        read=cached_read,
        repo_path=repo_path,
        revalidate_project_adapters=True,
    )
    registry.gate._terminal_remote_main_recheck(repo_path, observed_main)
    return slot_set


def load_workbuddy_slots(repo_path: str | Path = ".") -> tuple[WorkBuddySlot, ...]:
    return load_workbuddy_slot_set(repo_path).slots


def compatibility_legacy_projection(slot_set: WorkBuddySlotSet) -> Mapping[str, Any]:
    matches = [slot for slot in slot_set.slots if slot.legacy_default]
    if len(matches) != 1:
        raise WorkBuddySlotError("workbuddy_slots: legacy compatibility projection is not unique")
    legacy = matches[0]
    return {
        "schema": "WORKBUDDY_LEGACY_COMPATIBILITY_PROJECTION/v1",
        "projection_is_authority": False,
        "plural_authority_source": slot_set.registry_ref,
        "canonical_main_sha": slot_set.canonical_main_sha,
        "legacy_default_ref": slot_set.legacy_default_ref,
        "legacy_worker_slot_id": legacy.worker_slot_id,
        "legacy_task_id": legacy.task_id,
        "observed_workbuddy_slot_count": len(slot_set.slots),
        "bare_selection_safe_when_multiple": False,
        "explicit_selection_required_when_multiple": len(slot_set.slots) > 1,
    }


__all__ = [
    "ExecutionContractError", "WorkBuddySlotError", "WorkBuddySlot", "WorkBuddySlotSet",
    "build_slot_set_from_frozen_snapshot", "compatibility_legacy_projection",
    "load_workbuddy_slot_set", "load_workbuddy_slots",
]
