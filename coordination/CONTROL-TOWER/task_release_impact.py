from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from control_tower import classify_collision


CANDIDATE_SCHEMA = "TaskReleaseCandidate/v1"
RECEIPT_SCHEMA = "TaskReleaseImpactReceipt/v1"

REUSE_DECISIONS = frozenset(
    {
        "REUSE_AS_IS",
        "EXTEND",
        "WRAP_ADAPT",
        "MODIFY",
        "REPLACE",
        "MERGE",
        "DEPRECATE",
        "NEW_MODULE_JUSTIFIED",
        "REFERENCE_ONLY",
        "UNKNOWN",
    }
)
RELATION_TYPES = frozenset(
    {
        "REQUIRES",
        "REQUIRED_BY",
        "CONFLICTS_WITH",
        "OVERLAPS",
        "REUSES",
        "EXTENDS",
        "SUPERSEDES",
        "MUST_CHANGE_WITH",
        "PROVIDES_CAPABILITY",
        "CONSUMES_CAPABILITY",
        "AUTHORITY_OWNER",
        "WRITEBACK_OWNER",
        "CONTRACT_COMPATIBILITY",
        "MIGRATION_DEPENDENCY",
    }
)
CONSUMER_IMPACTS = frozenset(
    {
        "NO_CONSUMER_CHANGE",
        "CONSUMER_REVALIDATION_ONLY",
        "SYNCHRONIZED_CHANGE_REQUIRED",
        "MIGRATION_REQUIRED",
        "UNKNOWN_CONSUMERS_BLOCK_RELEASE",
    }
)
FINAL_DISPOSITIONS = frozenset(
    {
        "RELEASE_BOUNDED_TASK",
        "RELEASE_AS_EXTENSION",
        "RELEASE_AS_ADAPTER_OR_PLUGIN",
        "MERGE_WITH_EXISTING_TASK",
        "MODIFY_EXISTING_TASK",
        "DEFER_DEPENDENCY",
        "NEEDS_REVALIDATION",
        "ARCHITECTURE_CONFLICT",
        "NO_TASK_ALREADY_SATISFIED",
        "ABSTAIN",
    }
)
MATERIAL_LEVELS = frozenset({"TRIVIAL", "NORMAL", "MATERIAL", "HIGH"})
MATERIAL_SHARED_LEVELS = frozenset({"MATERIAL", "HIGH"})
MISSING_CAPABILITY_BEHAVIORS = frozenset({"UNSUPPORTED", "ABSTAIN", "NOT_APPLICABLE"})

_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "release_candidate_id",
        "source_signal_refs",
        "desired_effect",
        "observations",
        "proposed_target_domain",
        "proposed_write_surface",
        "materiality",
        "risk",
        "out_of_scope",
        "capability_inventory",
        "relations",
        "reverse_consumers",
        "consumer_inventory_complete",
        "authority_binding",
        "composition",
        "synchronized_change_set",
        "regression_revalidation_set",
        "unaffected_set",
        "unresolved_unknowns",
        "existing_work_items",
    }
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


def _deep_copy(value: Any) -> Any:
    return json.loads(_canonical(value))


def _nonempty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ImpactGateError("INVALID_STRING", path)
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ImpactGateError("INVALID_LIST", path)
    return value


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ImpactGateError("INVALID_MAPPING", path)
    return dict(value)


def _string_list(value: Any, path: str, *, nonempty: bool = False) -> list[str]:
    items = _list(value, path)
    if nonempty and not items:
        raise ImpactGateError("EMPTY_LIST_FORBIDDEN", path)
    for index, item in enumerate(items):
        _nonempty_string(item, f"{path}/{index}")
    return list(items)


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

    _nonempty_string(candidate["release_candidate_id"], "/release_candidate_id")
    _string_list(candidate["source_signal_refs"], "/source_signal_refs", nonempty=True)
    _nonempty_string(candidate["desired_effect"], "/desired_effect")
    _nonempty_string(candidate["proposed_target_domain"], "/proposed_target_domain")
    _string_list(candidate["risk"], "/risk")
    _string_list(candidate["out_of_scope"], "/out_of_scope")
    _string_list(candidate["synchronized_change_set"], "/synchronized_change_set")
    _string_list(candidate["regression_revalidation_set"], "/regression_revalidation_set")
    _string_list(candidate["unresolved_unknowns"], "/unresolved_unknowns")

    materiality = _nonempty_string(candidate["materiality"], "/materiality").upper()
    if materiality not in MATERIAL_LEVELS:
        raise ImpactGateError("INVALID_MATERIALITY", "/materiality")
    candidate["materiality"] = materiality

    observations = _list(candidate["observations"], "/observations")
    if not observations:
        raise ImpactGateError("CURRENT_OBSERVATION_REQUIRED", "/observations")
    for index, raw in enumerate(observations):
        observation = _mapping(raw, f"/observations/{index}")
        for field in ("scope", "revision", "evidence_ref"):
            if field not in observation:
                raise ImpactGateError("OBSERVATION_FIELD_MISSING", f"/observations/{index}/{field}")
            _nonempty_string(observation[field], f"/observations/{index}/{field}")
        status = str(observation.get("status", "CURRENT")).upper()
        if status not in {"CURRENT", "UNKNOWN", "STALE"}:
            raise ImpactGateError("INVALID_OBSERVATION_STATUS", f"/observations/{index}/status")

    surface = _mapping(candidate["proposed_write_surface"], "/proposed_write_surface")
    allowed_surface = {
        "write_paths",
        "read_paths",
        "interfaces",
        "read_domains",
        "write_domains",
        "authority_claims",
    }
    unexpected_surface = sorted(set(surface) - allowed_surface)
    if unexpected_surface:
        raise ImpactGateError("UNRECOGNIZED_WRITE_SURFACE_FIELD", f"/proposed_write_surface/{unexpected_surface[0]}")
    for key in ("write_paths", "read_paths", "read_domains", "write_domains", "authority_claims"):
        _string_list(surface.get(key, []), f"/proposed_write_surface/{key}")
    if not isinstance(surface.get("interfaces", []), list):
        raise ImpactGateError("INVALID_LIST", "/proposed_write_surface/interfaces")

    capabilities = _list(candidate["capability_inventory"], "/capability_inventory")
    for index, raw in enumerate(capabilities):
        capability = _mapping(raw, f"/capability_inventory/{index}")
        for field in ("component_id", "decision", "evidence_refs"):
            if field not in capability:
                raise ImpactGateError("CAPABILITY_FIELD_MISSING", f"/capability_inventory/{index}/{field}")
        _nonempty_string(capability["component_id"], f"/capability_inventory/{index}/component_id")
        decision = _nonempty_string(capability["decision"], f"/capability_inventory/{index}/decision").upper()
        if decision not in REUSE_DECISIONS:
            raise ImpactGateError("INVALID_REUSE_DECISION", f"/capability_inventory/{index}/decision")
        _string_list(capability["evidence_refs"], f"/capability_inventory/{index}/evidence_refs", nonempty=True)
        if decision == "NEW_MODULE_JUSTIFIED":
            justification = capability.get("new_module_justification")
            if not isinstance(justification, str) or not justification.strip():
                raise ImpactGateError(
                    "NEW_MODULE_JUSTIFICATION_REQUIRED",
                    f"/capability_inventory/{index}/new_module_justification",
                )
            if capability.get("existing_capabilities_insufficient") is not True:
                raise ImpactGateError(
                    "EXISTING_CAPABILITY_INSUFFICIENCY_NOT_PROVEN",
                    f"/capability_inventory/{index}/existing_capabilities_insufficient",
                )

    relations = _list(candidate["relations"], "/relations")
    for index, raw in enumerate(relations):
        relation = _mapping(raw, f"/relations/{index}")
        for field in ("relation", "source", "target", "evidence_refs"):
            if field not in relation:
                raise ImpactGateError("RELATION_FIELD_MISSING", f"/relations/{index}/{field}")
        relation_type = _nonempty_string(relation["relation"], f"/relations/{index}/relation").upper()
        if relation_type not in RELATION_TYPES:
            raise ImpactGateError("INVALID_RELATION_TYPE", f"/relations/{index}/relation")
        _nonempty_string(relation["source"], f"/relations/{index}/source")
        _nonempty_string(relation["target"], f"/relations/{index}/target")
        _string_list(relation["evidence_refs"], f"/relations/{index}/evidence_refs", nonempty=True)

    consumers = _list(candidate["reverse_consumers"], "/reverse_consumers")
    for index, raw in enumerate(consumers):
        consumer = _mapping(raw, f"/reverse_consumers/{index}")
        for field in ("consumer_id", "impact", "evidence_refs"):
            if field not in consumer:
                raise ImpactGateError("CONSUMER_FIELD_MISSING", f"/reverse_consumers/{index}/{field}")
        _nonempty_string(consumer["consumer_id"], f"/reverse_consumers/{index}/consumer_id")
        impact = _nonempty_string(consumer["impact"], f"/reverse_consumers/{index}/impact").upper()
        if impact not in CONSUMER_IMPACTS:
            raise ImpactGateError("INVALID_CONSUMER_IMPACT", f"/reverse_consumers/{index}/impact")
        _string_list(consumer["evidence_refs"], f"/reverse_consumers/{index}/evidence_refs", nonempty=True)
    if not isinstance(candidate["consumer_inventory_complete"], bool):
        raise ImpactGateError("INVALID_BOOLEAN", "/consumer_inventory_complete")

    authority = _mapping(candidate["authority_binding"], "/authority_binding")
    for field in ("owner_domain", "writeback_owner", "compatible"):
        if field not in authority:
            raise ImpactGateError("AUTHORITY_FIELD_MISSING", f"/authority_binding/{field}")
    _nonempty_string(authority["owner_domain"], "/authority_binding/owner_domain")
    _nonempty_string(authority["writeback_owner"], "/authority_binding/writeback_owner")
    if authority["compatible"] not in {True, False, "UNKNOWN"}:
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
    behavior = _nonempty_string(composition["missing_capability_behavior"], "/composition/missing_capability_behavior").upper()
    if behavior not in MISSING_CAPABILITY_BEHAVIORS:
        raise ImpactGateError("INVALID_MISSING_CAPABILITY_BEHAVIOR", "/composition/missing_capability_behavior")
    _nonempty_string(composition["justification"], "/composition/justification")
    if composition.get("removal_preserves_unrelated_core") not in {True, False, "UNKNOWN", None}:
        raise ImpactGateError("INVALID_REMOVAL_PROOF", "/composition/removal_preserves_unrelated_core")

    unaffected = _list(candidate["unaffected_set"], "/unaffected_set")
    for index, raw in enumerate(unaffected):
        item = _mapping(raw, f"/unaffected_set/{index}")
        _nonempty_string(item.get("component_id"), f"/unaffected_set/{index}/component_id")
        _string_list(item.get("evidence_refs"), f"/unaffected_set/{index}/evidence_refs", nonempty=True)

    existing = _list(candidate["existing_work_items"], "/existing_work_items")
    for index, raw in enumerate(existing):
        item = _mapping(raw, f"/existing_work_items/{index}")
        _nonempty_string(item.get("task_id"), f"/existing_work_items/{index}/task_id")
        if item.get("owns_coherent_change_surface") not in {True, False}:
            raise ImpactGateError(
                "INVALID_BOOLEAN", f"/existing_work_items/{index}/owns_coherent_change_surface"
            )

    return _deep_copy(candidate)


def _normalized_decisions(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "component_id": str(item["component_id"]),
            "decision": str(item["decision"]).upper(),
            "satisfies_requirement": bool(item.get("satisfies_requirement", False)),
            "evidence_refs": list(item["evidence_refs"]),
            **(
                {"task_ref": item["task_ref"]}
                if isinstance(item.get("task_ref"), str) and item.get("task_ref")
                else {}
            ),
        }
        for item in candidate["capability_inventory"]
    ]


def _normalized_relations(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "relation": str(item["relation"]).upper(),
            "source": item["source"],
            "target": item["target"],
            "evidence_refs": list(item["evidence_refs"]),
        }
        for item in candidate["relations"]
    ]


def _normalized_consumers(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "consumer_id": item["consumer_id"],
            "impact": str(item["impact"]).upper(),
            "evidence_refs": list(item["evidence_refs"]),
        }
        for item in candidate["reverse_consumers"]
    ]


def _collision_analysis(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    proposal = dict(candidate["proposed_write_surface"])
    results: list[dict[str, Any]] = []
    for item in candidate["existing_work_items"]:
        collision = classify_collision(proposal, dict(item))
        results.append(
            {
                "task_id": item["task_id"],
                "owns_coherent_change_surface": bool(item["owns_coherent_change_surface"]),
                **collision,
            }
        )
    return results


def _determine_disposition(
    candidate: Mapping[str, Any],
    decisions: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    consumers: list[dict[str, Any]],
    collisions: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    authority = candidate["authority_binding"]
    composition = candidate["composition"]

    if authority.get("would_create_second_writer") is True or authority.get("would_create_second_truth") is True:
        reasons.append("SECOND_WRITER_OR_TRUTH_FORBIDDEN")
        return "ARCHITECTURE_CONFLICT", reasons
    if authority["compatible"] is False:
        reasons.append("OWNER_DOMAIN_OR_WRITEBACK_INCOMPATIBLE")
        return "ARCHITECTURE_CONFLICT", reasons

    synchronized = set(candidate["synchronized_change_set"])
    missing_required = sorted(
        {
            relation["target"]
            for relation in relations
            if relation["relation"] == "MUST_CHANGE_WITH" and relation["target"] not in synchronized
        }
    )
    if missing_required:
        reasons.append("MUST_CHANGE_WITH_OUTSIDE_SYNCHRONIZED_SET:" + ",".join(missing_required))
        return "ARCHITECTURE_CONFLICT", reasons

    if composition["optional"] and composition["can_compose"]:
        if composition.get("removal_preserves_unrelated_core") is not True:
            reasons.append("OPTIONAL_COMPONENT_REMOVABILITY_NOT_PROVEN")
            return "ARCHITECTURE_CONFLICT", reasons
        if str(composition["missing_capability_behavior"]).upper() not in {"UNSUPPORTED", "ABSTAIN"}:
            reasons.append("OPTIONAL_COMPONENT_MISSING_BEHAVIOR_MUST_FAIL_CLOSED")
            return "ARCHITECTURE_CONFLICT", reasons

    coherent_owners = [item for item in collisions if item["owns_coherent_change_surface"]]
    if coherent_owners:
        reasons.append("EXISTING_ACTIVE_TASK_OWNS_COHERENT_CHANGE_SURFACE")
        return "MERGE_WITH_EXISTING_TASK", reasons

    if any(item["level"] == "O4" for item in collisions):
        reasons.append("AUTHORITY_COLLISION_WITH_EXISTING_WORK")
        return "ARCHITECTURE_CONFLICT", reasons
    if any(item["level"] == "O3" for item in collisions):
        reasons.append("MUTABLE_SURFACE_COLLISION_REQUIRES_SEQUENCE_OR_MERGE")
        return "DEFER_DEPENDENCY", reasons

    observation_statuses = {str(item.get("status", "CURRENT")).upper() for item in candidate["observations"]}
    unknown_consumer = any(item["impact"] == "UNKNOWN_CONSUMERS_BLOCK_RELEASE" for item in consumers)
    if (
        "UNKNOWN" in observation_statuses
        or "STALE" in observation_statuses
        or authority["compatible"] == "UNKNOWN"
        or unknown_consumer
        or (candidate["materiality"] in MATERIAL_SHARED_LEVELS and not candidate["consumer_inventory_complete"])
    ):
        reasons.append("CURRENT_SYSTEM_OR_CONSUMER_EVIDENCE_INCOMPLETE")
        return "NEEDS_REVALIDATION", reasons

    if candidate["unresolved_unknowns"] and candidate["materiality"] in MATERIAL_SHARED_LEVELS:
        reasons.append("MATERIAL_UNKNOWNS_PRESERVED")
        return "NEEDS_REVALIDATION", reasons

    if not decisions or all(item["decision"] in {"UNKNOWN", "REFERENCE_ONLY"} for item in decisions):
        reasons.append("NO_ACTIONABLE_REUSE_OR_CHANGE_DECISION")
        return "ABSTAIN", reasons

    satisfied = [item for item in decisions if item["decision"] == "REUSE_AS_IS" and item["satisfies_requirement"]]
    if satisfied and not any(
        item["decision"] in {"EXTEND", "WRAP_ADAPT", "MODIFY", "REPLACE", "MERGE", "NEW_MODULE_JUSTIFIED"}
        for item in decisions
    ):
        reasons.append("EXISTING_CAPABILITY_ALREADY_SATISFIES_DESIRED_EFFECT")
        return "NO_TASK_ALREADY_SATISFIED", reasons

    if any(item["decision"] == "WRAP_ADAPT" for item in decisions) and composition["optional"] and composition["can_compose"]:
        reasons.append("OPTIONAL_CAPABILITY_COMPOSED_THROUGH_STABLE_CONTRACT")
        return "RELEASE_AS_ADAPTER_OR_PLUGIN", reasons

    if any(item["decision"] == "EXTEND" for item in decisions):
        reasons.append("EXISTING_CAPABILITY_SHOULD_BE_EXTENDED")
        return "RELEASE_AS_EXTENSION", reasons

    if any(item["decision"] == "MODIFY" and item.get("task_ref") for item in decisions):
        reasons.append("EXISTING_TASK_SHOULD_BE_MODIFIED")
        return "MODIFY_EXISTING_TASK", reasons

    reasons.append("BOUNDED_COHERENT_CHANGE_SET_READY_FOR_EXISTING_CONTROL_TOWER")
    return "RELEASE_BOUNDED_TASK", reasons


def evaluate_release_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return deterministic evidence for the existing Control Tower release decision.

    This function never creates a Task, Route, Claim, lease, write permission, domain authority,
    Signal, W3 object, or merge authorization. It only evaluates the candidate's declared,
    evidence-bound architecture surface and emits a receipt for downstream governance.
    """

    candidate = validate_release_candidate(value)
    decisions = _normalized_decisions(candidate)
    relations = _normalized_relations(candidate)
    consumers = _normalized_consumers(candidate)
    collisions = _collision_analysis(candidate)
    disposition, reasons = _determine_disposition(candidate, decisions, relations, consumers, collisions)
    if disposition not in FINAL_DISPOSITIONS:
        raise AssertionError(f"unsupported final disposition: {disposition}")

    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "release_candidate_id": candidate["release_candidate_id"],
        "source_signal_refs": list(candidate["source_signal_refs"]),
        "input_digest": _digest(candidate),
        "exact_observations": _deep_copy(candidate["observations"]),
        "capability_reuse_decisions": decisions,
        "relation_impact_edges": relations,
        "reverse_consumer_analysis": consumers,
        "consumer_inventory_complete": bool(candidate["consumer_inventory_complete"]),
        "authority_writeback_binding": _deep_copy(candidate["authority_binding"]),
        "composition_removability_decision": _deep_copy(candidate["composition"]),
        "synchronized_change_set": list(candidate["synchronized_change_set"]),
        "regression_revalidation_set": list(candidate["regression_revalidation_set"]),
        "unaffected_set": _deep_copy(candidate["unaffected_set"]),
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
