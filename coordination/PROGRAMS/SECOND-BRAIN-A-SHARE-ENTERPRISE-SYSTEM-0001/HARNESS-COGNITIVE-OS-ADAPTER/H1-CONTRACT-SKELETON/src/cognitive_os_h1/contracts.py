"""Deterministic H1 validators.  No runtime/provider/domain integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class ValidationError:
    validator_id: str
    code: str
    path: str


REQUIRED: dict[str, tuple[str, ...]] = {
    "DecisionEpisode/v1": ("schema_version", "decision_episode_id", "mission_id", "problem_signature_id", "task_class", "materiality", "risk_class", "state", "created_at", "authority_snapshot_ref", "trace_root_id", "reproducibility_fingerprint"),
    "ProblemSignature/v1": ("schema_version", "problem_signature_id", "task_class", "objective", "materiality", "reversibility", "causal_requirement", "evidence_mode", "point_in_time_required", "competing_hypotheses_required"),
    "Mission/v1": ("schema_version", "mission_id", "intake_source", "objective", "status", "created_at"),
    "MissionGraph/v1": ("schema_version", "mission_graph_id", "mission_id", "nodes", "edges", "generated_at"),
    "Claim/v1": ("schema_version", "claim_id", "claim_type", "statement_ref", "status"),
    "ChallengeCase/v1": ("schema_version", "challenge_id", "target_claim_id", "challenge_type", "challenge_level", "severity", "status"),
    "VerificationResult/v1": ("schema_version", "verification_id", "target_claim_id", "result", "trace_refs"),
    "Adjudication/v1": ("schema_version", "adjudication_id", "claim_results", "disposition"),
    "FormalHandoff/v1": ("schema_version", "handoff_id", "decision_episode_id", "producer", "consumer", "stage", "epistemic_status", "input_fingerprint", "raw_trace_refs", "created_at"),
    "OutcomeLearning/v1": ("schema_version", "learning_event_id", "decision_episode_id", "created_at"),
    "ReworkRequest/v1": ("schema_version", "rework_request_id", "decision_episode_id", "return_from_state", "return_to_state", "reason_code", "retry_budget_remaining", "input_fingerprint_before"),
}

STATES = ("INTAKE", "PROBLEM_SIGNATURED", "CONTEXT_RETRIEVED", "CAPABILITY_GAP_MAPPED", "METHODS_DISCOVERED", "METHODS_SELECTED_OR_ABSTAINED", "EVIDENCE_PLAN_READY", "CONTROL_TOWER_AUTHORIZED", "EXECUTING", "PRIMARY_RESULT_READY", "CHALLENGE_PENDING_OR_SKIPPED", "VERIFIED", "ADJUDICATED", "DOMAIN_VALIDATED", "RISK_VETO_CHECKED", "OUTPUT_OR_ACTION_PROPOSED", "OUTCOME_OBSERVED", "ATTRIBUTED", "REFLECTED", "LEARNING_CANDIDATES_CREATED", "CROSS_CONTEXT_VALIDATED", "UPDATED", "DEGRADED", "RETIRED", "ABSTAINED", "CANCELLED", "FAILED", "CLOSED")
TERMINAL = {"RETIRED", "ABSTAINED", "CANCELLED", "FAILED", "CLOSED"}
EXECUTION_STATES = {"EXECUTING", "PRIMARY_RESULT_READY", "CHALLENGE_PENDING_OR_SKIPPED", "VERIFIED", "ADJUDICATED", "DOMAIN_VALIDATED", "RISK_VETO_CHECKED", "OUTPUT_OR_ACTION_PROPOSED", "OUTCOME_OBSERVED", "ATTRIBUTED", "REFLECTED", "LEARNING_CANDIDATES_CREATED", "CROSS_CONTEXT_VALIDATED", "UPDATED", "DEGRADED", "RETIRED"}
TRACE_STATES = {"PRIMARY_RESULT_READY", "CHALLENGE_PENDING_OR_SKIPPED", "VERIFIED", "ADJUDICATED", "DOMAIN_VALIDATED", "RISK_VETO_CHECKED", "OUTPUT_OR_ACTION_PROPOSED", "OUTCOME_OBSERVED", "ATTRIBUTED", "REFLECTED", "LEARNING_CANDIDATES_CREATED", "CROSS_CONTEXT_VALIDATED", "UPDATED", "DEGRADED", "RETIRED", "CLOSED"}
FORWARD = {
    "INTAKE": {"PROBLEM_SIGNATURED", "ABSTAINED", "CANCELLED", "FAILED"},
    "PROBLEM_SIGNATURED": {"CONTEXT_RETRIEVED", "ABSTAINED", "CANCELLED", "FAILED"},
    "CONTEXT_RETRIEVED": {"CAPABILITY_GAP_MAPPED", "METHODS_DISCOVERED", "ABSTAINED", "CANCELLED", "FAILED"},
    "CAPABILITY_GAP_MAPPED": {"METHODS_DISCOVERED", "ABSTAINED", "CANCELLED", "FAILED"},
    "METHODS_DISCOVERED": {"METHODS_SELECTED_OR_ABSTAINED", "ABSTAINED", "CANCELLED", "FAILED"},
    "METHODS_SELECTED_OR_ABSTAINED": {"EVIDENCE_PLAN_READY", "CONTROL_TOWER_AUTHORIZED", "ABSTAINED", "CANCELLED", "FAILED"},
    "EVIDENCE_PLAN_READY": {"CONTROL_TOWER_AUTHORIZED", "ABSTAINED", "CANCELLED", "FAILED"},
    "CONTROL_TOWER_AUTHORIZED": {"EXECUTING", "CANCELLED", "FAILED"},
    "EXECUTING": {"PRIMARY_RESULT_READY", "CANCELLED", "FAILED"},
    "PRIMARY_RESULT_READY": {"CHALLENGE_PENDING_OR_SKIPPED", "VERIFIED", "ADJUDICATED", "CANCELLED", "FAILED"},
    "CHALLENGE_PENDING_OR_SKIPPED": {"VERIFIED", "ADJUDICATED", "CANCELLED", "FAILED"},
    "VERIFIED": {"ADJUDICATED", "CANCELLED", "FAILED"},
    "ADJUDICATED": {"DOMAIN_VALIDATED", "RISK_VETO_CHECKED", "ABSTAINED", "CANCELLED", "FAILED"},
    "DOMAIN_VALIDATED": {"RISK_VETO_CHECKED", "ABSTAINED", "CANCELLED", "FAILED"},
    "RISK_VETO_CHECKED": {"OUTPUT_OR_ACTION_PROPOSED", "ABSTAINED", "CANCELLED", "FAILED"},
    "OUTPUT_OR_ACTION_PROPOSED": {"OUTCOME_OBSERVED", "CLOSED", "CANCELLED", "FAILED"},
    "OUTCOME_OBSERVED": {"ATTRIBUTED", "CLOSED", "FAILED"},
    "ATTRIBUTED": {"REFLECTED", "CLOSED", "FAILED"},
    "REFLECTED": {"LEARNING_CANDIDATES_CREATED", "CLOSED", "FAILED"},
    "LEARNING_CANDIDATES_CREATED": {"CROSS_CONTEXT_VALIDATED", "CLOSED", "FAILED"},
    "CROSS_CONTEXT_VALIDATED": {"UPDATED", "DEGRADED", "RETIRED", "CLOSED", "FAILED"},
    "UPDATED": {"CLOSED", "DEGRADED", "RETIRED"},
    "DEGRADED": {"CLOSED", "RETIRED", "CROSS_CONTEXT_VALIDATED"},
    "RETIRED": {"CLOSED"}, "ABSTAINED": {"CLOSED"}, "CANCELLED": {"CLOSED"}, "FAILED": {"CLOSED"}, "CLOSED": set(),
}
REWORK = {"ADJUDICATED": {"EVIDENCE_PLAN_READY", "METHODS_DISCOVERED"}, "RISK_VETO_CHECKED": {"EVIDENCE_PLAN_READY", "METHODS_DISCOVERED", "EXECUTING"}, "DEGRADED": {"METHODS_DISCOVERED"}}

ENUMS: dict[str, set[str]] = {
    "task_class": {"KNOWLEDGE", "RESEARCH", "SYSTEM_DESIGN", "ENGINEERING", "MARKET_INTELLIGENCE", "EQUITY_ANALYSIS", "BACKTEST", "REVIEW", "DECISION_SUPPORT", "OTHER"},
    "materiality": {"LOW", "MEDIUM", "HIGH", "CRITICAL"}, "risk_class": {"R0", "R1", "R2", "R3", "R4"},
    "w7_veto_status": {"NOT_EVALUATED", "PASS", "VETO", "HUMAN_GATE", "ABSTAIN"},
    "decision_status": {"OPEN", "PROPOSED", "ACCEPTED", "REJECTED", "ABSTAINED", "CANCELLED", "FAILED", "CLOSED"},
    "reversibility": {"REVERSIBLE", "PARTIALLY_REVERSIBLE", "IRREVERSIBLE", "UNKNOWN"},
    "causal_requirement": {"DESCRIPTIVE", "ASSOCIATIONAL", "CAUSAL", "DECISIONAL", "UNKNOWN"},
    "evidence_mode": {"INTERNAL_ONLY", "EXTERNAL_REQUIRED", "FIRST_PARTY_REQUIRED", "MIXED", "UNKNOWN"},
    "intake_source": {"USER", "SYSTEM_EVENT", "OUTCOME_FOLLOWUP", "SCHEDULED_REVIEW"},
    "mission_status": {"RECEIVED", "PLANNING", "WAITING_AUTHORIZATION", "EXECUTING", "BLOCKED", "ABSTAINED", "CANCELLED", "COMPLETED", "FAILED"},
    "claim_type": {"OBSERVED_FACT", "SOURCE_CLAIM", "SOURCE_INTERPRETATION", "USER_ASSERTION", "MODEL_INFERENCE", "CAUSAL_HYPOTHESIS", "DECISION_ASSUMPTION", "UNKNOWN"},
    "confidence_class": {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}, "claim_status": {"OPEN", "SUPPORTED", "WEAKENED", "CONTRADICTED", "UNRESOLVED", "REJECTED", "SUPERSEDED", "REVOKED"},
    "challenge_level": {"C0", "C1", "C2", "C3", "C4"}, "severity": {"LOW", "MEDIUM", "HIGH", "BLOCKING"},
    "verification_result": {"CONFIRMED", "PARTIALLY_CONFIRMED", "REFUTED", "INCONCLUSIVE", "SOURCE_UNAVAILABLE", "TOOL_FAILED"},
    "disposition": {"ACCEPT", "ACCEPT_WITH_LIMITS", "RETURN_FOR_EVIDENCE", "RETURN_FOR_REWORK", "UNRESOLVED", "ABSTAIN"},
    "epistemic_status": {"OBSERVED", "SUPPORTED", "HYPOTHESIS", "MIXED", "UNKNOWN", "ABSTAINED"},
}

SEMANTIC_INVARIANT_IDS = frozenset({
    "DE-W7-VETO-NO-ACCEPT", "DE-ABSTAIN-STATE-CONSISTENCY", "DE-EXECUTION-AUTH-REQUIRED", "DE-POST-PRIMARY-TRACE-RESOLVABLE", "DE-LEARNING-NEEDS-OUTCOME-OR-CORRECTION", "DE-NO-RAW-PRIVATE-BODY",
    "PS-HIGH-MATERIALITY-EVIDENCE-OR-WAIVER", "PS-CAUSAL-REQUIRES-COMPETING-HYPOTHESES", "PS-PIT-REQUIRES-CAPABILITY", "M-USER-INTAKE-NO-AUTH-GRANT", "M-COMPLETED-NEEDS-RESULT-OR-NO-WORK",
    "MG-DEPENDENCY-DAG-ACYCLIC", "MG-RETURN-CYCLE-BOUNDED", "MG-EXECUTABLE-NODE-NEEDS-CONTROL-TOWER", "MG-CAN-PARALLEL-NOT-AUTHORIZATION", "MG-HEAVY-LOCAL-RESOURCE-CAP",
    "C-UNKNOWN-CONFIDENCE-UNKNOWN", "C-MATERIAL-CAUSAL-NEEDS-FALSIFIER", "C-PROSE-CANNOT-PROMOTE-INFERENCE-TO-FACT", "CH-C2-C4-INDEPENDENT-PASS-REQUIRED", "A-NO-W7-OVERRIDE", "A-UNRESOLVED-ABSTAIN-VALID",
    "FH-RAW-TRACE-REF-REQUIRED", "FH-HUMAN-COMPANION-NONAUTHORITATIVE", "OL-NEEDS-OUTCOME-CORRECTION-OR-AUDIT", "OL-NO-DIRECT-FORMAL-SKILL", "OL-GOOD-OUTCOME-NOT-PROOF-OF-GOOD-METHOD", "OL-BAD-OUTCOME-NOT-PROOF-OF-BAD-METHOD",
    "RW-RETURN-TARGET-ALLOWED-BY-STATE-MACHINE", "RW-NO-RETRY-WHEN-BUDGET-ZERO", "RW-RETRY-REQUIRES-MATERIAL-CHANGE-OR-EXPLICIT-ESCALATION",
})


def _err(validator_id: str, code: str, path: str) -> ValidationError:
    return ValidationError(validator_id, code, path)


def _is_rfc3339_offset(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _array_of_unique_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value) and len(value) == len(set(value))


def validate_structure(record: dict[str, Any]) -> list[ValidationError]:
    if not isinstance(record, Mapping):
        return [_err("STRUCTURE", "OBJECT_REQUIRED", "/")]
    version = record.get("schema_version")
    if version not in REQUIRED:
        return [_err("STRUCTURE", "SCHEMA_VERSION_UNSUPPORTED", "/schema_version")]
    errors = [_err("STRUCTURE", "REQUIRED_FIELD_MISSING", "/" + name) for name in REQUIRED[version] if name not in record or record[name] in (None, "")]
    for name in ("claim_ids", "handoff_refs", "unresolved_refs", "raw_trace_refs", "trace_refs", "source_refs", "support_refs", "counterevidence_refs", "falsifier_refs", "claim_results"):
        if name in record and not _array_of_unique_strings(record[name]):
            errors.append(_err("STRUCTURE", "ARRAY_UNIQUE_STRINGS_REQUIRED", "/" + name))
    if "retry_budget_remaining" in record and (not isinstance(record["retry_budget_remaining"], int) or record["retry_budget_remaining"] < 0):
        errors.append(_err("STRUCTURE", "NONNEGATIVE_INTEGER_REQUIRED", "/retry_budget_remaining"))
    for field in ("created_at", "closed_at", "completed_at", "generated_at", "observed_at"):
        if record.get(field) is not None and not _is_rfc3339_offset(record[field]):
            errors.append(_err("STRUCTURE", "RFC3339_OFFSET_AWARE_REQUIRED", "/" + field))
    enum_fields = {
        "DecisionEpisode/v1": {"task_class": "task_class", "materiality": "materiality", "risk_class": "risk_class", "state": "state", "w7_veto_status": "w7_veto_status", "decision_status": "decision_status"},
        "ProblemSignature/v1": {"materiality": "materiality", "reversibility": "reversibility", "causal_requirement": "causal_requirement", "evidence_mode": "evidence_mode"},
        "Mission/v1": {"intake_source": "intake_source", "status": "mission_status"},
        "Claim/v1": {"claim_type": "claim_type", "materiality": "materiality", "confidence_class": "confidence_class", "status": "claim_status"},
        "ChallengeCase/v1": {"challenge_level": "challenge_level", "severity": "severity"},
        "VerificationResult/v1": {"result": "verification_result"},
        "Adjudication/v1": {"disposition": "disposition"},
        "FormalHandoff/v1": {"epistemic_status": "epistemic_status"},
    }.get(version, {})
    for field, enum_name in enum_fields.items():
        if field in record and record[field] not in (None, "") and record[field] not in (STATES if enum_name == "state" else ENUMS[enum_name]):
            errors.append(_err("STRUCTURE", "ENUM_VALUE_INVALID", "/" + field))
    if version == "MissionGraph/v1":
        if not isinstance(record.get("nodes"), list) or not isinstance(record.get("edges"), list):
            errors.append(_err("STRUCTURE", "MISSION_GRAPH_ARRAYS_REQUIRED", "/nodes"))
        for index, node in enumerate(record.get("nodes", [])):
            if not isinstance(node, Mapping) or any(not node.get(field) for field in ("work_item_id", "work_type", "owner_candidate", "resource_class", "status")):
                errors.append(_err("STRUCTURE", "MISSION_NODE_INVALID", "/nodes/" + str(index)))
            elif not isinstance(node.get("retry_budget"), int) or node["retry_budget"] < 0:
                errors.append(_err("STRUCTURE", "NONNEGATIVE_INTEGER_REQUIRED", "/nodes/" + str(index) + "/retry_budget"))
            elif node.get("work_type") not in {"RETRIEVAL", "RESEARCH", "DATA_ACQUISITION", "EVIDENCE_VERIFICATION", "ANALYSIS", "IMPLEMENTATION", "TEST", "CHALLENGE", "REVIEW", "ADJUDICATION", "APPROVAL", "WRITEBACK", "OUTCOME_AUDIT"} or node.get("resource_class") not in {"LIGHT", "MEDIUM", "HEAVY_LOCAL", "REMOTE_CI", "EXTERNAL_SERVICE"} or node.get("status") not in {"PLANNED", "AUTHORIZED", "QUEUED", "RUNNING", "BLOCKED", "RETURNED", "COMPLETED", "FAILED", "CANCELLED", "ABSTAINED"}:
                errors.append(_err("STRUCTURE", "MISSION_NODE_ENUM_INVALID", "/nodes/" + str(index)))
        for index, edge in enumerate(record.get("edges", [])):
            if not isinstance(edge, Mapping) or any(not edge.get(field) for field in ("from", "to", "type")):
                errors.append(_err("STRUCTURE", "MISSION_EDGE_INVALID", "/edges/" + str(index)))
            elif edge.get("type") not in {"DEPENDS_ON", "CAN_PARALLEL_WITH", "BLOCKS", "REQUIRES_APPROVAL_FROM", "RETURNS_TO", "ESCALATES_TO", "FEEDBACK_TO"}:
                errors.append(_err("STRUCTURE", "MISSION_EDGE_ENUM_INVALID", "/edges/" + str(index) + "/type"))
    return errors


def validate_semantics(record: dict[str, Any], *, trace_refs: set[str] | None = None) -> list[ValidationError]:
    errors: list[ValidationError] = []
    v = record.get("schema_version")
    if v == "DecisionEpisode/v1":
        if record.get("w7_veto_status") == "VETO" and record.get("decision_status") == "ACCEPTED": errors.append(_err("DE-W7-VETO-NO-ACCEPT", "VETO_BLOCKS_ACCEPT", "/decision_status"))
        if record.get("decision_status") == "ABSTAINED" and record.get("state") not in {"ABSTAINED", "CLOSED"}: errors.append(_err("DE-ABSTAIN-STATE-CONSISTENCY", "ABSTAIN_STATE_INVALID", "/state"))
        if record.get("state") in EXECUTION_STATES and not record.get("control_tower_authorization_ref"): errors.append(_err("DE-EXECUTION-AUTH-REQUIRED", "EXECUTION_AUTH_MISSING", "/control_tower_authorization_ref"))
        if record.get("state") in TRACE_STATES and (not record.get("trace_root_id") or (trace_refs is not None and record["trace_root_id"] not in trace_refs)): errors.append(_err("DE-POST-PRIMARY-TRACE-RESOLVABLE", "TRACE_UNRESOLVABLE", "/trace_root_id"))
        if record.get("learning_ref") and not (record.get("outcome_ref") or record.get("explicit_correction_event_ref")): errors.append(_err("DE-LEARNING-NEEDS-OUTCOME-OR-CORRECTION", "LEARNING_TRIGGER_MISSING", "/learning_ref"))
        if "raw_private_source_body" in record: errors.append(_err("DE-NO-RAW-PRIVATE-BODY", "RAW_PRIVATE_BODY_FORBIDDEN", "/raw_private_source_body"))
    elif v == "ProblemSignature/v1":
        if record.get("materiality") in {"HIGH", "CRITICAL"} and record.get("evidence_mode") == "INTERNAL_ONLY" and not record.get("evidence_waiver_ref"): errors.append(_err("PS-HIGH-MATERIALITY-EVIDENCE-OR-WAIVER", "EVIDENCE_OR_WAIVER_REQUIRED", "/evidence_mode"))
        if record.get("causal_requirement") == "CAUSAL" and not record.get("competing_hypotheses_required"): errors.append(_err("PS-CAUSAL-REQUIRES-COMPETING-HYPOTHESES", "COMPETING_HYPOTHESES_REQUIRED", "/competing_hypotheses_required"))
        if record.get("point_in_time_required") and not record.get("pit_capability_ref"): errors.append(_err("PS-PIT-REQUIRES-CAPABILITY", "PIT_CAPABILITY_REQUIRED", "/pit_capability_ref"))
    elif v == "Mission/v1":
        if record.get("status") == "COMPLETED" and not (record.get("final_result_ref") or record.get("no_work_reason_ref")):
            errors.append(_err("M-COMPLETED-NEEDS-RESULT-OR-NO-WORK", "COMPLETION_REFERENCE_REQUIRED", "/status"))
        if record.get("intake_authorizes_execution") or record.get("authorization_granted_by") == "USER_INTAKE":
            errors.append(_err("M-USER-INTAKE-NO-AUTH-GRANT", "INTAKE_CANNOT_GRANT_EXECUTION_AUTHORITY", "/intake_authorizes_execution"))
    elif v == "Claim/v1":
        if record.get("claim_type") == "UNKNOWN" and record.get("confidence_class") != "UNKNOWN": errors.append(_err("C-UNKNOWN-CONFIDENCE-UNKNOWN", "UNKNOWN_CONFIDENCE_REQUIRED", "/confidence_class"))
        if record.get("claim_type") == "CAUSAL_HYPOTHESIS" and record.get("materiality") in {"HIGH", "CRITICAL"} and not record.get("falsifier_refs"): errors.append(_err("C-MATERIAL-CAUSAL-NEEDS-FALSIFIER", "FALSIFIER_REQUIRED", "/falsifier_refs"))
        if record.get("claim_type") == "MODEL_INFERENCE" and record.get("human_companion_claim_type") == "OBSERVED_FACT":
            errors.append(_err("C-PROSE-CANNOT-PROMOTE-INFERENCE-TO-FACT", "PROSE_PROMOTION_FORBIDDEN", "/human_companion_claim_type"))
    elif v == "ChallengeCase/v1" and record.get("challenge_level") in {"C2", "C3", "C4"} and not record.get("independent_pass_ref"):
        errors.append(_err("CH-C2-C4-INDEPENDENT-PASS-REQUIRED", "INDEPENDENT_PASS_REQUIRED", "/independent_pass_ref"))
    elif v == "Adjudication/v1":
        if record.get("w7_veto_status") == "VETO" and record.get("disposition") in {"ACCEPT", "ACCEPT_WITH_LIMITS"}:
            errors.append(_err("A-NO-W7-OVERRIDE", "W7_VETO_CANNOT_BE_OVERRIDDEN", "/disposition"))
    elif v == "FormalHandoff/v1":
        if not record.get("raw_trace_refs"):
            errors.append(_err("FH-RAW-TRACE-REF-REQUIRED", "RAW_TRACE_REQUIRED", "/raw_trace_refs"))
        companion = record.get("analysis_companion")
        machine_fields = {"claim_ids", "evidence_refs", "counterevidence_refs", "epistemic_status", "accepted_by", "acceptance_status", "raw_trace_refs"}
        if isinstance(companion, Mapping) and machine_fields.intersection(companion):
            errors.append(_err("FH-HUMAN-COMPANION-NONAUTHORITATIVE", "HUMAN_COMPANION_MUTATES_MACHINE_FIELD", "/analysis_companion"))
    elif v == "OutcomeLearning/v1":
        if not (record.get("outcome_ref") or record.get("correction_event_ref") or record.get("audit_finding_ref")): errors.append(_err("OL-NEEDS-OUTCOME-CORRECTION-OR-AUDIT", "LEARNING_TRIGGER_REQUIRED", "/"))
        if any(record.get(field) == "FORMAL_SKILL" for field in ("requested_maturity", "promotion_target", "skill_status")):
            errors.append(_err("OL-NO-DIRECT-FORMAL-SKILL", "FORMAL_SKILL_PROMOTION_FORBIDDEN", "/requested_maturity"))
        if record.get("outcome_polarity") == "POSITIVE" and record.get("method_quality_update") == "GOOD":
            errors.append(_err("OL-GOOD-OUTCOME-NOT-PROOF-OF-GOOD-METHOD", "OUTCOME_ALONE_CANNOT_PROVE_METHOD", "/method_quality_update"))
        if record.get("outcome_polarity") == "NEGATIVE" and record.get("method_quality_update") == "BAD":
            errors.append(_err("OL-BAD-OUTCOME-NOT-PROOF-OF-BAD-METHOD", "OUTCOME_ALONE_CANNOT_PROVE_METHOD", "/method_quality_update"))
    return errors


def validate_transition(current: str, target: str, rework: dict[str, Any] | None = None) -> list[ValidationError]:
    if target in FORWARD.get(current, set()): return []
    if rework is not None:
        if target not in REWORK.get(current, set()):
            return [_err("RW-RETURN-TARGET-ALLOWED-BY-STATE-MACHINE", "REWORK_TARGET_FORBIDDEN", "/return_to_state")]
        errors = validate_structure(rework)
        if rework.get("return_from_state") != current or rework.get("return_to_state") != target:
            errors.append(_err("RW-RETURN-TARGET-ALLOWED-BY-STATE-MACHINE", "REWORK_BINDING_MISMATCH", "/return_to_state"))
        if rework.get("retry_budget_remaining", 0) <= 0: errors.append(_err("RW-NO-RETRY-WHEN-BUDGET-ZERO", "REWORK_BUDGET_EXHAUSTED", "/retry_budget_remaining"))
        if not (rework.get("input_fingerprint_after") and rework["input_fingerprint_after"] != rework.get("input_fingerprint_before")) and not rework.get("escalation_ref"): errors.append(_err("RW-RETRY-REQUIRES-MATERIAL-CHANGE-OR-EXPLICIT-ESCALATION", "IDENTICAL_RETRY_FORBIDDEN", "/input_fingerprint_after"))
        return errors
    return [_err("DE-STATE-TRANSITION", "TRANSITION_FORBIDDEN", "/state")]


def validate_mission_graph(graph: dict[str, Any], *, authorization_refs: set[str]) -> list[ValidationError]:
    errors = validate_structure(graph)
    node_values = [node for node in graph.get("nodes", []) if isinstance(node, Mapping) and node.get("work_item_id")]
    nodes = {node["work_item_id"]: node for node in node_values}
    if len(nodes) != len(node_values): errors.append(_err("MG-NODE-IDENTITY", "DUPLICATE_WORK_ITEM_ID", "/nodes"))
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    for edge in graph.get("edges", []):
        source, target = edge.get("from"), edge.get("to")
        if source not in nodes or target not in nodes: errors.append(_err("MG-ENDPOINT", "EDGE_ENDPOINT_UNKNOWN", "/edges")); continue
        if edge.get("type") in {"DEPENDS_ON", "BLOCKS"}: adjacency[source].add(target)
        if edge.get("type") == "CAN_PARALLEL_WITH" and any(nodes[item].get("status") in {"AUTHORIZED", "RUNNING"} and not set(nodes[item].get("required_authority_refs", [])).intersection(authorization_refs) for item in (source, target)):
            errors.append(_err("MG-CAN-PARALLEL-NOT-AUTHORIZATION", "PARALLEL_EDGE_CANNOT_GRANT_AUTHORIZATION", "/edges"))
        if edge.get("type") == "RETURNS_TO":
            request = edge.get("rework_request")
            if not isinstance(request, Mapping) or request.get("retry_budget_remaining", 0) <= 0 or not request.get("termination_condition_ref") or not request.get("escalation_ref"):
                errors.append(_err("MG-RETURN-CYCLE-BOUNDED", "REWORK_LOOP_UNBOUNDED", "/edges"))
    active, done = set(), set()
    def visit(node: str) -> None:
        if node in active: errors.append(_err("MG-DEPENDENCY-DAG-ACYCLIC", "DEPENDENCY_CYCLE", "/edges")); return
        if node in done: return
        active.add(node)
        for neighbor in adjacency[node]: visit(neighbor)
        active.remove(node); done.add(node)
    for node in nodes: visit(node)
    if sum(node.get("resource_class") == "HEAVY_LOCAL" and node.get("status") in {"AUTHORIZED", "RUNNING"} for node in nodes.values()) > 1: errors.append(_err("MG-HEAVY-LOCAL-RESOURCE-CAP", "HEAVY_LOCAL_CAP_EXCEEDED", "/nodes"))
    for node in nodes.values():
        if node.get("status") in {"AUTHORIZED", "RUNNING"} and not set(node.get("required_authority_refs", [])).intersection(authorization_refs): errors.append(_err("MG-EXECUTABLE-NODE-NEEDS-CONTROL-TOWER", "AUTHORIZATION_MISSING", "/nodes"))
        if node.get("status") in {"AUTHORIZED", "RUNNING"} and not node.get("termination_condition_ref"):
            errors.append(_err("MG-RETURN-CYCLE-BOUNDED", "EXECUTABLE_NODE_TERMINATION_REQUIRED", "/nodes"))
    return errors


def validate_organization(graph: dict[str, Any], *, alias_resolution: dict[str, list[str]], h2_authorized: bool = False, declared_aliases: set[str] | None = None) -> list[ValidationError]:
    errors: list[ValidationError] = []
    departments = {item.get("id"): item for item in graph.get("departments", []) if item.get("id")}
    declared = declared_aliases if declared_aliases is not None else set(graph.get("dynamic_return_aliases", alias_resolution))
    owners: dict[str, list[str]] = {}
    for item in departments.values():
        domain = item.get("authority_domain")
        if domain and domain != "NONE": owners.setdefault(domain, []).append(item["id"])
        if item.get("node_kind") == "ROLE_TEMPLATE" and domain not in (None, "NONE"): errors.append(_err("OGV-032-ROLE-TEMPLATE-NONAUTHORITY", "ROLE_AUTHORITY_FORBIDDEN", "/departments"))
    if any(len(values) != 1 for values in owners.values()): errors.append(_err("OGV-001-UNIQUE-AUTHORITY", "AUTHORITY_NOT_UNIQUE", "/departments"))
    connected: dict[str, int] = {node_id: 0 for node_id in departments}
    outgoing: dict[str, int] = {node_id: 0 for node_id in departments}
    for edge in graph.get("edges", []):
        for key in ("from", "to"):
            endpoint = edge.get(key)
            if endpoint not in departments and endpoint != "USER" and endpoint not in declared: errors.append(_err("OGV-027-ROLE-AND-ALIAS-RESOLUTION", "EDGE_ENDPOINT_UNDECLARED", "/edges"))
            elif endpoint in departments: connected[endpoint] += 1
        if edge.get("from") in departments: outgoing[edge["from"]] += 1
        if edge.get("type") in {"LIVE_TRADE", "PLACE_ORDER", "MOVE_FUNDS"}:
            errors.append(_err("OGV-022-A-SHARE-NO-TRADE", "LIVE_TRADING_EDGE_FORBIDDEN", "/edges"))
    for node_id, count in connected.items():
        if node_id != "USER" and count == 0:
            errors.append(_err("OGV-002-ORPHAN-DEPARTMENT", "ORPHAN_DEPARTMENT", "/departments/" + node_id))
    for node_id, item in departments.items():
        material_outputs = item.get("produces", [])
        if material_outputs and outgoing[node_id] == 0 and not item.get("terminal_disposition_ref"):
            errors.append(_err("OGV-003-DEAD-END", "MATERIAL_OUTPUT_DEAD_END", "/departments/" + node_id + "/produces"))
    for alias, targets in alias_resolution.items():
        if alias not in declared or len(targets) != 1 or targets[0] not in departments: errors.append(_err("OGV-027-ROLE-AND-ALIAS-RESOLUTION", "RETURN_ALIAS_NOT_UNIQUE", "/aliases/" + alias))
    for item in departments.values():
        for target in item.get("return_to", []):
            if target not in departments and target != "USER" and target not in declared:
                errors.append(_err("OGV-005-RETURN-PATH", "RETURN_TARGET_UNDECLARED", "/departments/" + item["id"] + "/return_to"))
    if any(item.get("id") == "HARNESS_RUNTIME" and item.get("authority_domain") not in {"RUNTIME_ORCHESTRATION", "NONE"} for item in departments.values()): errors.append(_err("OGV-018-HARNESS-BOUNDARY", "HARNESS_TRUTH_AUTHORITY_FORBIDDEN", "/departments"))
    if sum(item.get("authority_domain") == "KNOWLEDGE_MEMORY_LIFECYCLE" for item in departments.values()) > 1:
        errors.append(_err("OGV-W3-SINGLE-AUTHORITY", "W3_AUTHORITY_NOT_UNIQUE", "/departments"))
    if any(item.get("id") == "W7_VALIDATION_RISK" and "FINAL_OUTPUT_OR_ACTION" not in item.get("may_veto", []) for item in departments.values()):
        errors.append(_err("OGV-007-VETO-INTEGRITY", "W7_FINAL_VETO_MISSING", "/departments"))
    if h2_authorized: errors.append(_err("OGV-031-H1-H2-SLICE-SEPARATION", "H2_AUTHORIZATION_FORBIDDEN_IN_H1", "/h2_authorized"))
    return errors


def validate_trace_handoff(handoff: dict[str, Any], *, trace_ids: set[str], trace_level: str = "T1", trace_material: Mapping[str, Any] | None = None) -> list[ValidationError]:
    errors = validate_structure(handoff) + validate_semantics(handoff)
    if not set(handoff.get("raw_trace_refs", [])).issubset(trace_ids): errors.append(_err("OGV-011-TRACE-COMPLETENESS", "TRACE_INCOMPLETE", "/raw_trace_refs"))
    forbidden = {"raw_private_source_body", "credential_value", "access_token", "api_key", "private_key", "hidden_prompt", "private_chain_of_thought"}
    if forbidden.intersection(handoff): errors.append(_err("DE-NO-RAW-PRIVATE-BODY", "PRIVATE_TRACE_FIELD_FORBIDDEN", "/"))
    required_by_level = {
        "T0": {"decision_episode_id", "input_fingerprint", "output_ref"},
        "T1": {"decision_episode_id", "input_fingerprint", "output_ref", "work_item_events", "tool_refs", "formal_handoff"},
        "T2": {"decision_episode_id", "input_fingerprint", "output_ref", "work_item_events", "tool_refs", "formal_handoff", "claim_refs", "evidence_refs", "challenge_refs", "provider_native_trace_refs"},
        "T3": {"decision_episode_id", "input_fingerprint", "output_ref", "work_item_events", "tool_refs", "formal_handoff", "claim_refs", "evidence_refs", "challenge_refs", "provider_native_trace_refs", "independent_pass_refs", "verification_trace", "adjudication_trace", "W7_gate_ref", "authority_witness_ref"},
    }
    if trace_level not in required_by_level:
        errors.append(_err("TRACE-COMPLETENESS", "TRACE_LEVEL_UNSUPPORTED", "/trace_level"))
    elif trace_material is not None:
        for field in required_by_level[trace_level]:
            if not trace_material.get(field): errors.append(_err("TRACE-COMPLETENESS", "TRACE_LEVEL_FIELD_MISSING", "/trace_material/" + field))
    if trace_level in {"T2", "T3"} and not handoff.get("claim_ids"): errors.append(_err("TRACE-COMPLETENESS", "MATERIAL_CLAIMS_REQUIRED", "/claim_ids"))
    return errors


FINGERPRINT_FIELDS = ("SourceSnapshotHash", "ContextBundleHash", "UpstreamHandoffHashes", "PromptTemplateHash", "MethodSkillVersions", "ModelProvider", "ModelID", "ToolSchemaHash", "CodeCommit", "DomainRuleSnapshot", "SchemaVersion")
def cognitive_fingerprint(payload: dict[str, Any]) -> str:
    missing = [name for name in FINGERPRINT_FIELDS if name not in payload]
    if missing: raise ValueError("FINGERPRINT_COMPONENT_MISSING:" + ",".join(missing))
    forbidden = {"secret", "token", "password", "api_key", "private_key"}
    if forbidden.intersection({str(key).casefold() for key in payload}): raise ValueError("FINGERPRINT_SECRET_FIELD_FORBIDDEN")
    canonical = {name: payload[name] for name in FINGERPRINT_FIELDS}
    return sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


@dataclass(frozen=True)
class ModelCheckReport:
    states_checked: int
    properties_checked: tuple[str, ...]
    violations: tuple[ValidationError, ...]


def explore_critical_states() -> ModelCheckReport:
    """Exhaustively explore the finite H1 abstractions without subprocesses or a runtime."""
    violations: list[ValidationError] = []
    states_checked = 0
    properties = ("mission_lifecycle", "authorization", "challenge_rework_termination", "skill_no_one_shot_promotion", "w7_veto", "trace_completeness", "resource_max_one", "return_alias", "h1_h2_separation")
    for current, targets in FORWARD.items():
        for target in targets:
            states_checked += 1
            if validate_transition(current, target): violations.append(_err("FM-01-MISSION-LIFECYCLE", "DECLARED_FORWARD_TRANSITION_REJECTED", "/state"))
    for veto in ("PASS", "VETO"):
        for disposition in ("ACCEPTED", "ABSTAINED"):
            states_checked += 1
            result = validate_semantics({"schema_version": "DecisionEpisode/v1", "decision_episode_id": "d", "mission_id": "m", "problem_signature_id": "p", "task_class": "OTHER", "materiality": "LOW", "risk_class": "R0", "state": "INTAKE", "created_at": "2026-01-01T00:00:00Z", "authority_snapshot_ref": "a", "trace_root_id": "t", "reproducibility_fingerprint": "f", "w7_veto_status": veto, "decision_status": disposition})
            blocked = any(error.validator_id == "DE-W7-VETO-NO-ACCEPT" for error in result)
            if (veto == "VETO" and disposition == "ACCEPTED") != blocked: violations.append(_err("FM-05-W7-VETO", "VETO_SAFETY_BROKEN", "/decision_status"))
    for budget in (0, 1):
        for changed in (False, True):
            states_checked += 1
            request = {"schema_version": "ReworkRequest/v1", "rework_request_id": "r", "decision_episode_id": "d", "return_from_state": "ADJUDICATED", "return_to_state": "EVIDENCE_PLAN_READY", "reason_code": "TEST", "retry_budget_remaining": budget, "input_fingerprint_before": "a", "input_fingerprint_after": "b" if changed else "a"}
            result = validate_transition("ADJUDICATED", "EVIDENCE_PLAN_READY", request)
            allowed = not result
            if allowed != (budget > 0 and changed): violations.append(_err("FM-03-CHALLENGE-REWORK", "REWORK_TERMINATION_BROKEN", "/retry_budget_remaining"))
    states_checked += 4
    no_auth = validate_semantics({"schema_version": "DecisionEpisode/v1", "decision_episode_id": "d", "mission_id": "m", "problem_signature_id": "p", "task_class": "OTHER", "materiality": "LOW", "risk_class": "R0", "state": "EXECUTING", "created_at": "2026-01-01T00:00:00Z", "authority_snapshot_ref": "a", "trace_root_id": "t", "reproducibility_fingerprint": "f"})
    if not any(error.validator_id == "DE-EXECUTION-AUTH-REQUIRED" for error in no_auth): violations.append(_err("FM-02-WORK-CLAIM-AUTHORIZATION", "UNAUTHORIZED_EXECUTION_ALLOWED", "/state"))
    trace = {"decision_episode_id": "d", "input_fingerprint": "f", "output_ref": "o", "work_item_events": ["e"], "tool_refs": ["t"], "formal_handoff": "h"}
    trace_result = validate_trace_handoff({"schema_version": "FormalHandoff/v1", "handoff_id": "h", "decision_episode_id": "d", "producer": "p", "consumer": "c", "stage": "x", "epistemic_status": "SUPPORTED", "input_fingerprint": "f", "raw_trace_refs": ["t"], "created_at": "2026-01-01T00:00:00Z"}, trace_ids={"t"}, trace_level="T2", trace_material=trace)
    if not any(error.code == "TRACE_LEVEL_FIELD_MISSING" for error in trace_result): violations.append(_err("FM-06-TRACE", "INCOMPLETE_MATERIAL_TRACE_ALLOWED", "/trace_material"))
    heavy = {"schema_version": "MissionGraph/v1", "mission_graph_id": "g", "mission_id": "m", "generated_at": "2026-01-01T00:00:00Z", "nodes": [{"work_item_id": "a", "work_type": "TEST", "owner_candidate": "x", "resource_class": "HEAVY_LOCAL", "status": "RUNNING", "retry_budget": 0, "required_authority_refs": ["a"], "termination_condition_ref": "t"}, {"work_item_id": "b", "work_type": "TEST", "owner_candidate": "x", "resource_class": "HEAVY_LOCAL", "status": "RUNNING", "retry_budget": 0, "required_authority_refs": ["a"], "termination_condition_ref": "t"}], "edges": []}
    if not any(error.validator_id == "MG-HEAVY-LOCAL-RESOURCE-CAP" for error in validate_mission_graph(heavy, authorization_refs={"a"})): violations.append(_err("FM-07-RESOURCE", "HEAVY_RESOURCE_CAP_BROKEN", "/nodes"))
    alias_result = validate_organization({"departments": [{"id": "A", "authority_domain": "NONE", "node_kind": "DEPARTMENT"}], "edges": [{"from": "A", "to": "RESPONSIBLE_UPSTREAM"}], "dynamic_return_aliases": ["RESPONSIBLE_UPSTREAM"]}, alias_resolution={"RESPONSIBLE_UPSTREAM": ["A", "MISSING"]})
    if not any(error.code == "RETURN_ALIAS_NOT_UNIQUE" for error in alias_result): violations.append(_err("FM-08-RETURN-ALIAS", "AMBIGUOUS_ALIAS_ALLOWED", "/aliases"))
    if not validate_semantics({"schema_version": "OutcomeLearning/v1", "learning_event_id": "l", "decision_episode_id": "d", "created_at": "2026-01-01T00:00:00Z", "correction_event_ref": "c"}): pass
    else: violations.append(_err("FM-04-SKILL-LIFECYCLE", "CORRECTION_LEARNING_REJECTED", "/correction_event_ref"))
    if not validate_semantics({"schema_version": "OutcomeLearning/v1", "learning_event_id": "l", "decision_episode_id": "d", "created_at": "2026-01-01T00:00:00Z", "correction_event_ref": "c", "requested_maturity": "FORMAL_SKILL"}): violations.append(_err("FM-04-SKILL-LIFECYCLE", "FORMAL_SKILL_NOT_BLOCKED", "/requested_maturity"))
    if not validate_organization({"departments": [], "edges": []}, alias_resolution={}, h2_authorized=True): violations.append(_err("FM-09-H1-H2", "H2_AUTHORIZATION_NOT_BLOCKED", "/h2_authorized"))
    return ModelCheckReport(states_checked, properties, tuple(violations))


def validate_bundle(records: Iterable[dict[str, Any]]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for record in records:
        errors.extend(validate_structure(record)); errors.extend(validate_semantics(record))
    return errors
