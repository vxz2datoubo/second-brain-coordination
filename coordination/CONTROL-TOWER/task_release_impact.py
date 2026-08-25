from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from control_tower import classify_collision


CANDIDATE_SCHEMA = "TaskReleaseCandidate/v1"
RECEIPT_SCHEMA = "TaskReleaseImpactReceipt/v1"

REUSE_DECISIONS = frozenset({
    "REUSE_AS_IS", "EXTEND", "WRAP_ADAPT", "MODIFY", "REPLACE", "MERGE",
    "DEPRECATE", "NEW_MODULE_JUSTIFIED", "REFERENCE_ONLY", "UNKNOWN",
})
RELATION_TYPES = frozenset({
    "REQUIRES", "REQUIRED_BY", "CONFLICTS_WITH", "OVERLAPS", "REUSES",
    "EXTENDS", "SUPERSEDES", "MUST_CHANGE_WITH", "PROVIDES_CAPABILITY",
    "CONSUMES_CAPABILITY", "AUTHORITY_OWNER", "WRITEBACK_OWNER",
    "CONTRACT_COMPATIBILITY", "MIGRATION_DEPENDENCY",
})
CONSUMER_IMPACTS = frozenset({
    "NO_CONSUMER_CHANGE", "CONSUMER_REVALIDATION_ONLY",
    "SYNCHRONIZED_CHANGE_REQUIRED", "MIGRATION_REQUIRED",
    "UNKNOWN_CONSUMERS_BLOCK_RELEASE",
})
FINAL_DISPOSITIONS = frozenset({
    "RELEASE_BOUNDED_TASK", "RELEASE_AS_EXTENSION", "RELEASE_AS_ADAPTER_OR_PLUGIN",
    "MERGE_WITH_EXISTING_TASK", "MODIFY_EXISTING_TASK", "DEFER_DEPENDENCY",
    "NEEDS_REVALIDATION", "ARCHITECTURE_CONFLICT", "NO_TASK_ALREADY_SATISFIED",
    "ABSTAIN",
})
MATERIAL_LEVELS = frozenset({"TRIVIAL", "NORMAL", "MATERIAL", "HIGH"})
MATERIAL_SHARED_LEVELS = frozenset({"MATERIAL", "HIGH"})
MISSING_CAPABILITY_BEHAVIORS = frozenset({"UNSUPPORTED", "ABSTAIN", "NOT_APPLICABLE"})

_REQUIRED_FIELDS = frozenset({
    "schema_version", "release_candidate_id", "source_signal_refs", "desired_effect",
    "observations", "proposed_target_domain", "proposed_write_surface", "materiality",
    "risk", "out_of_scope", "capability_inventory", "relations", "reverse_consumers",
    "consumer_inventory_complete", "authority_binding", "composition",
    "synchronized_change_set", "regression_revalidation_set", "unaffected_set",
    "unresolved_unknowns", "existing_work_items",
})
_COLLISION_FIELDS = (
    "write_paths", "read_paths", "interfaces", "read_domains", "write_domains",
    "authority_claims",
)
_COLLISION_STRING_FIELDS = (
    "write_paths", "read_paths", "read_domains", "write_domains", "authority_claims",
)


class ImpactGateError(ValueError):
    """Fail-closed R149 contract error."""

    def __init__(self, code: str, path: str = "/") -> None:
        super().__init__(code)
        self.code = code
        self.path = path


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _copy(value: Any) -> Any:
    return json.loads(_canonical(value))


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ImpactGateError("INVALID_MAPPING", path)
    return dict(value)


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ImpactGateError("INVALID_LIST", path)
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ImpactGateError("INVALID_STRING", path)
    return value


def _strings(value: Any, path: str, *, nonempty: bool = False) -> list[str]:
    items = _list(value, path)
    if nonempty and not items:
        raise ImpactGateError("EMPTY_LIST_FORBIDDEN", path)
    for index, item in enumerate(items):
        _string(item, f"{path}/{index}")
    return list(items)


def _interfaces(value: Any, path: str) -> None:
    for index, raw in enumerate(_list(value, path)):
        item_path = f"{path}/{index}"
        if isinstance(raw, str):
            _string(raw, item_path)
            continue
        item = _mapping(raw, item_path)
        _string(item.get("name"), f"{item_path}/name")
        if "mode" in item and _string(item["mode"], f"{item_path}/mode").lower() not in {"read", "write"}:
            raise ImpactGateError("INVALID_INTERFACE_MODE", f"{item_path}/mode")
        if "frozen" in item and not isinstance(item["frozen"], bool):
            raise ImpactGateError("INVALID_BOOLEAN", f"{item_path}/frozen")


def validate_release_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _mapping(value, "/")
    missing = sorted(_REQUIRED_FIELDS - set(candidate))
    if missing:
        raise ImpactGateError("MISSING_REQUIRED_FIELD", f"/{missing[0]}")
    unexpected = sorted(set(candidate) - _REQUIRED_FIELDS)
    if unexpected:
        raise ImpactGateError("UNRECOGNIZED_FIELD", f"/{unexpected[0]}")
    if candidate["schema_version"] != CANDIDATE_SCHEMA:
        raise ImpactGateError("INVALID_SCHEMA_VERSION", "/schema_version")

    _string(candidate["release_candidate_id"], "/release_candidate_id")
    _strings(candidate["source_signal_refs"], "/source_signal_refs", nonempty=True)
    _string(candidate["desired_effect"], "/desired_effect")
    _string(candidate["proposed_target_domain"], "/proposed_target_domain")
    for name in ("risk", "out_of_scope", "synchronized_change_set", "regression_revalidation_set", "unresolved_unknowns"):
        _strings(candidate[name], f"/{name}")

    materiality = _string(candidate["materiality"], "/materiality").upper()
    if materiality not in MATERIAL_LEVELS:
        raise ImpactGateError("INVALID_MATERIALITY", "/materiality")
    candidate["materiality"] = materiality

    observations = _list(candidate["observations"], "/observations")
    if not observations:
        raise ImpactGateError("CURRENT_OBSERVATION_REQUIRED", "/observations")
    for index, raw in enumerate(observations):
        item = _mapping(raw, f"/observations/{index}")
        for field in ("scope", "revision", "evidence_ref"):
            if field not in item:
                raise ImpactGateError("OBSERVATION_FIELD_MISSING", f"/observations/{index}/{field}")
            _string(item[field], f"/observations/{index}/{field}")
        if str(item.get("status", "CURRENT")).upper() not in {"CURRENT", "UNKNOWN", "STALE"}:
            raise ImpactGateError("INVALID_OBSERVATION_STATUS", f"/observations/{index}/status")

    surface = _mapping(candidate["proposed_write_surface"], "/proposed_write_surface")
    extra = sorted(set(surface) - set(_COLLISION_FIELDS))
    if extra:
        raise ImpactGateError("UNRECOGNIZED_WRITE_SURFACE_FIELD", f"/proposed_write_surface/{extra[0]}")
    for field in _COLLISION_STRING_FIELDS:
        _strings(surface.get(field, []), f"/proposed_write_surface/{field}")
    _interfaces(surface.get("interfaces", []), "/proposed_write_surface/interfaces")

    for index, raw in enumerate(_list(candidate["capability_inventory"], "/capability_inventory")):
        item = _mapping(raw, f"/capability_inventory/{index}")
        for field in ("component_id", "decision", "evidence_refs"):
            if field not in item:
                raise ImpactGateError("CAPABILITY_FIELD_MISSING", f"/capability_inventory/{index}/{field}")
        _string(item["component_id"], f"/capability_inventory/{index}/component_id")
        decision = _string(item["decision"], f"/capability_inventory/{index}/decision").upper()
        if decision not in REUSE_DECISIONS:
            raise ImpactGateError("INVALID_REUSE_DECISION", f"/capability_inventory/{index}/decision")
        _strings(item["evidence_refs"], f"/capability_inventory/{index}/evidence_refs", nonempty=True)
        if "satisfies_requirement" in item and not isinstance(item["satisfies_requirement"], bool):
            raise ImpactGateError("INVALID_BOOLEAN", f"/capability_inventory/{index}/satisfies_requirement")
        if "task_ref" in item:
            _string(item["task_ref"], f"/capability_inventory/{index}/task_ref")
        if decision == "NEW_MODULE_JUSTIFIED":
            if not isinstance(item.get("new_module_justification"), str) or not item["new_module_justification"].strip():
                raise ImpactGateError("NEW_MODULE_JUSTIFICATION_REQUIRED", f"/capability_inventory/{index}/new_module_justification")
            if item.get("existing_capabilities_insufficient") is not True:
                raise ImpactGateError("EXISTING_CAPABILITY_INSUFFICIENCY_NOT_PROVEN", f"/capability_inventory/{index}/existing_capabilities_insufficient")

    for index, raw in enumerate(_list(candidate["relations"], "/relations")):
        item = _mapping(raw, f"/relations/{index}")
        for field in ("relation", "source", "target", "evidence_refs"):
            if field not in item:
                raise ImpactGateError("RELATION_FIELD_MISSING", f"/relations/{index}/{field}")
        relation = _string(item["relation"], f"/relations/{index}/relation").upper()
        if relation not in RELATION_TYPES:
            raise ImpactGateError("INVALID_RELATION_TYPE", f"/relations/{index}/relation")
        _string(item["source"], f"/relations/{index}/source")
        _string(item["target"], f"/relations/{index}/target")
        _strings(item["evidence_refs"], f"/relations/{index}/evidence_refs", nonempty=True)

    for index, raw in enumerate(_list(candidate["reverse_consumers"], "/reverse_consumers")):
        item = _mapping(raw, f"/reverse_consumers/{index}")
        for field in ("consumer_id", "impact", "evidence_refs"):
            if field not in item:
                raise ImpactGateError("CONSUMER_FIELD_MISSING", f"/reverse_consumers/{index}/{field}")
        _string(item["consumer_id"], f"/reverse_consumers/{index}/consumer_id")
        if _string(item["impact"], f"/reverse_consumers/{index}/impact").upper() not in CONSUMER_IMPACTS:
            raise ImpactGateError("INVALID_CONSUMER_IMPACT", f"/reverse_consumers/{index}/impact")
        _strings(item["evidence_refs"], f"/reverse_consumers/{index}/evidence_refs", nonempty=True)
    if not isinstance(candidate["consumer_inventory_complete"], bool):
        raise ImpactGateError("INVALID_BOOLEAN", "/consumer_inventory_complete")

    authority = _mapping(candidate["authority_binding"], "/authority_binding")
    for field in ("owner_domain", "writeback_owner", "compatible"):
        if field not in authority:
            raise ImpactGateError("AUTHORITY_FIELD_MISSING", f"/authority_binding/{field}")
    _string(authority["owner_domain"], "/authority_binding/owner_domain")
    _string(authority["writeback_owner"], "/authority_binding/writeback_owner")
    compatible = authority["compatible"]
    if not (isinstance(compatible, bool) or compatible == "UNKNOWN"):
        raise ImpactGateError("INVALID_AUTHORITY_COMPATIBILITY", "/authority_binding/compatible")
    for field in ("would_create_second_writer", "would_create_second_truth"):
        if field in authority and not isinstance(authority[field], bool):
            raise ImpactGateError("INVALID_BOOLEAN", f"/authority_binding/{field}")

    composition = _mapping(candidate["composition"], "/composition")
    for field in ("optional", "can_compose", "core_invariant", "missing_capability_behavior", "justification"):
        if field not in composition:
            raise ImpactGateError("COMPOSITION_FIELD_MISSING", f"/composition/{field}")
    for field in ("optional", "can_compose", "core_invariant"):
        if not isinstance(composition[field], bool):
            raise ImpactGateError("INVALID_BOOLEAN", f"/composition/{field}")
    if _string(composition["missing_capability_behavior"], "/composition/missing_capability_behavior").upper() not in MISSING_CAPABILITY_BEHAVIORS:
        raise ImpactGateError("INVALID_MISSING_CAPABILITY_BEHAVIOR", "/composition/missing_capability_behavior")
    _string(composition["justification"], "/composition/justification")
    removal = composition.get("removal_preserves_unrelated_core")
    if not (removal is None or isinstance(removal, bool) or removal == "UNKNOWN"):
        raise ImpactGateError("INVALID_REMOVAL_PROOF", "/composition/removal_preserves_unrelated_core")

    for index, raw in enumerate(_list(candidate["unaffected_set"], "/unaffected_set")):
        item = _mapping(raw, f"/unaffected_set/{index}")
        _string(item.get("component_id"), f"/unaffected_set/{index}/component_id")
        _strings(item.get("evidence_refs"), f"/unaffected_set/{index}/evidence_refs", nonempty=True)

    for index, raw in enumerate(_list(candidate["existing_work_items"], "/existing_work_items")):
        path = f"/existing_work_items/{index}"
        item = _mapping(raw, path)
        _string(item.get("task_id"), f"{path}/task_id")
        if not isinstance(item.get("owns_coherent_change_surface"), bool):
            raise ImpactGateError("INVALID_BOOLEAN", f"{path}/owns_coherent_change_surface")
        missing_collision = [field for field in _COLLISION_FIELDS if field not in item]
        if missing_collision:
            raise ImpactGateError("EXISTING_WORK_COLLISION_EVIDENCE_INCOMPLETE", f"{path}/{missing_collision[0]}")
        for field in _COLLISION_STRING_FIELDS:
            _strings(item[field], f"{path}/{field}")
        _interfaces(item["interfaces"], f"{path}/interfaces")

    return _copy(candidate)


def _decisions(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{
        "component_id": str(item["component_id"]),
        "decision": str(item["decision"]).upper(),
        "satisfies_requirement": bool(item.get("satisfies_requirement", False)),
        "evidence_refs": list(item["evidence_refs"]),
        **({"task_ref": item["task_ref"]} if isinstance(item.get("task_ref"), str) and item.get("task_ref") else {}),
    } for item in candidate["capability_inventory"]]


def _relations(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{
        "relation": str(item["relation"]).upper(), "source": item["source"],
        "target": item["target"], "evidence_refs": list(item["evidence_refs"]),
    } for item in candidate["relations"]]


def _consumers(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{
        "consumer_id": item["consumer_id"], "impact": str(item["impact"]).upper(),
        "evidence_refs": list(item["evidence_refs"]),
    } for item in candidate["reverse_consumers"]]


def _collisions(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    proposal = dict(candidate["proposed_write_surface"])
    result = []
    for item in candidate["existing_work_items"]:
        result.append({
            "task_id": item["task_id"],
            "owns_coherent_change_surface": bool(item["owns_coherent_change_surface"]),
            **classify_collision(proposal, dict(item)),
        })
    return result


def _consumer_set_conflicts(candidate: Mapping[str, Any], consumers: list[dict[str, Any]]) -> list[str]:
    synchronized = set(candidate["synchronized_change_set"])
    revalidation = set(candidate["regression_revalidation_set"])
    reasons = []
    missing_sync = sorted(item["consumer_id"] for item in consumers if item["impact"] == "SYNCHRONIZED_CHANGE_REQUIRED" and item["consumer_id"] not in synchronized)
    if missing_sync:
        reasons.append("REVERSE_CONSUMER_SYNC_SET_INCOMPLETE:" + ",".join(missing_sync))
    missing_revalidation = sorted(item["consumer_id"] for item in consumers if item["impact"] == "CONSUMER_REVALIDATION_ONLY" and item["consumer_id"] not in revalidation)
    if missing_revalidation:
        reasons.append("REVERSE_CONSUMER_REVALIDATION_SET_INCOMPLETE:" + ",".join(missing_revalidation))
    missing_migration_sync = sorted(item["consumer_id"] for item in consumers if item["impact"] == "MIGRATION_REQUIRED" and item["consumer_id"] not in synchronized)
    missing_migration_revalidation = sorted(item["consumer_id"] for item in consumers if item["impact"] == "MIGRATION_REQUIRED" and item["consumer_id"] not in revalidation)
    if missing_migration_sync or missing_migration_revalidation:
        parts = []
        if missing_migration_sync:
            parts.append("sync=" + ",".join(missing_migration_sync))
        if missing_migration_revalidation:
            parts.append("revalidate=" + ",".join(missing_migration_revalidation))
        reasons.append("REVERSE_CONSUMER_MIGRATION_SET_INCOMPLETE:" + ";".join(parts))
    return reasons


def _disposition(candidate, decisions, relations, consumers, collisions):
    authority = candidate["authority_binding"]
    composition = candidate["composition"]
    if authority.get("would_create_second_writer") is True or authority.get("would_create_second_truth") is True:
        return "ARCHITECTURE_CONFLICT", ["SECOND_WRITER_OR_TRUTH_FORBIDDEN"]
    if authority["compatible"] is False:
        return "ARCHITECTURE_CONFLICT", ["OWNER_DOMAIN_OR_WRITEBACK_INCOMPATIBLE"]

    synchronized = set(candidate["synchronized_change_set"])
    missing_required = sorted({item["target"] for item in relations if item["relation"] == "MUST_CHANGE_WITH" and item["target"] not in synchronized})
    if missing_required:
        return "ARCHITECTURE_CONFLICT", ["MUST_CHANGE_WITH_OUTSIDE_SYNCHRONIZED_SET:" + ",".join(missing_required)]
    consumer_conflicts = _consumer_set_conflicts(candidate, consumers)
    if consumer_conflicts:
        return "ARCHITECTURE_CONFLICT", consumer_conflicts

    if composition["optional"] and composition["can_compose"]:
        if composition.get("removal_preserves_unrelated_core") is not True:
            return "ARCHITECTURE_CONFLICT", ["OPTIONAL_COMPONENT_REMOVABILITY_NOT_PROVEN"]
        if str(composition["missing_capability_behavior"]).upper() not in {"UNSUPPORTED", "ABSTAIN"}:
            return "ARCHITECTURE_CONFLICT", ["OPTIONAL_COMPONENT_MISSING_BEHAVIOR_MUST_FAIL_CLOSED"]

    if any(item["owns_coherent_change_surface"] for item in collisions):
        return "MERGE_WITH_EXISTING_TASK", ["EXISTING_ACTIVE_TASK_OWNS_COHERENT_CHANGE_SURFACE"]
    if any(item["level"] == "O4" for item in collisions):
        return "ARCHITECTURE_CONFLICT", ["AUTHORITY_COLLISION_WITH_EXISTING_WORK"]
    if any(item["level"] == "O3" for item in collisions):
        return "DEFER_DEPENDENCY", ["MUTABLE_SURFACE_COLLISION_REQUIRES_SEQUENCE_OR_MERGE"]

    statuses = {str(item.get("status", "CURRENT")).upper() for item in candidate["observations"]}
    unknown_consumer = any(item["impact"] == "UNKNOWN_CONSUMERS_BLOCK_RELEASE" for item in consumers)
    if "UNKNOWN" in statuses or "STALE" in statuses or authority["compatible"] == "UNKNOWN" or unknown_consumer or (candidate["materiality"] in MATERIAL_SHARED_LEVELS and not candidate["consumer_inventory_complete"]):
        return "NEEDS_REVALIDATION", ["CURRENT_SYSTEM_OR_CONSUMER_EVIDENCE_INCOMPLETE"]
    if candidate["unresolved_unknowns"] and candidate["materiality"] in MATERIAL_SHARED_LEVELS:
        return "NEEDS_REVALIDATION", ["MATERIAL_UNKNOWNS_PRESERVED"]
    if not decisions or all(item["decision"] in {"UNKNOWN", "REFERENCE_ONLY"} for item in decisions):
        return "ABSTAIN", ["NO_ACTIONABLE_REUSE_OR_CHANGE_DECISION"]

    satisfied = [item for item in decisions if item["decision"] == "REUSE_AS_IS" and item["satisfies_requirement"]]
    if satisfied and not any(item["decision"] in {"EXTEND", "WRAP_ADAPT", "MODIFY", "REPLACE", "MERGE", "NEW_MODULE_JUSTIFIED"} for item in decisions):
        return "NO_TASK_ALREADY_SATISFIED", ["EXISTING_CAPABILITY_ALREADY_SATISFIES_DESIRED_EFFECT"]
    if any(item["decision"] == "WRAP_ADAPT" for item in decisions) and composition["optional"] and composition["can_compose"]:
        return "RELEASE_AS_ADAPTER_OR_PLUGIN", ["OPTIONAL_CAPABILITY_COMPOSED_THROUGH_STABLE_CONTRACT"]
    if any(item["decision"] == "EXTEND" for item in decisions):
        return "RELEASE_AS_EXTENSION", ["EXISTING_CAPABILITY_SHOULD_BE_EXTENDED"]
    if any(item["decision"] == "MODIFY" and item.get("task_ref") for item in decisions):
        return "MODIFY_EXISTING_TASK", ["EXISTING_TASK_SHOULD_BE_MODIFIED"]
    return "RELEASE_BOUNDED_TASK", ["BOUNDED_COHERENT_CHANGE_SET_READY_FOR_EXISTING_CONTROL_TOWER"]


def evaluate_release_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return deterministic evidence for the existing Control Tower release decision.

    This remains evidence-only. It never creates a Task, Route, Work Claim, execution
    authority, domain write permission, Signal, W3 object, or merge authorization.
    """
    candidate = validate_release_candidate(value)
    decisions = _decisions(candidate)
    relations = _relations(candidate)
    consumers = _consumers(candidate)
    collisions = _collisions(candidate)
    disposition, reasons = _disposition(candidate, decisions, relations, consumers, collisions)
    if disposition not in FINAL_DISPOSITIONS:
        raise AssertionError(f"unsupported final disposition: {disposition}")
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "release_candidate_id": candidate["release_candidate_id"],
        "source_signal_refs": list(candidate["source_signal_refs"]),
        "input_digest": _digest(candidate),
        "exact_observations": _copy(candidate["observations"]),
        "capability_reuse_decisions": decisions,
        "relation_impact_edges": relations,
        "reverse_consumer_analysis": consumers,
        "consumer_inventory_complete": bool(candidate["consumer_inventory_complete"]),
        "authority_writeback_binding": _copy(candidate["authority_binding"]),
        "composition_removability_decision": _copy(candidate["composition"]),
        "synchronized_change_set": list(candidate["synchronized_change_set"]),
        "regression_revalidation_set": list(candidate["regression_revalidation_set"]),
        "unaffected_set": _copy(candidate["unaffected_set"]),
        "unresolved_unknowns": list(candidate["unresolved_unknowns"]),
        "collision_analysis": collisions,
        "final_disposition": disposition,
        "reasons": reasons,
        "authority_boundary": {
            "evidence_only": True,
            "creates_task": False,
            "creates_route": False,
            "creates_work_claim": False,
            "grants_execution_authority": False,
            "grants_domain_write": False,
            "grants_merge_authority": False,
        },
    }
    receipt["receipt_digest"] = _digest(receipt)
    return receipt
