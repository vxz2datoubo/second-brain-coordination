"""Deterministic H1 validators.  No runtime/provider/domain integration."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Iterable


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
    "Adjudication/v1": ("schema_version", "adjudication_id", "claim_results", "disposition", "rubric_ref"),
    "FormalHandoff/v1": ("schema_version", "handoff_id", "decision_episode_id", "producer", "consumer", "stage", "epistemic_status", "input_fingerprint", "raw_trace_refs", "created_at"),
    "OutcomeLearning/v1": ("schema_version", "learning_event_id", "decision_episode_id", "created_at"),
    "ReworkRequest/v1": ("schema_version", "rework_request_id", "decision_episode_id", "return_from_state", "return_to_state", "reason_code", "retry_budget_remaining", "input_fingerprint_before"),
}

STATES = ("INTAKE", "PROBLEM_SIGNATURED", "CONTEXT_RETRIEVED", "CAPABILITY_GAP_MAPPED", "METHODS_DISCOVERED", "METHODS_SELECTED_OR_ABSTAINED", "EVIDENCE_PLAN_READY", "CONTROL_TOWER_AUTHORIZED", "EXECUTING", "PRIMARY_RESULT_READY", "CHALLENGE_PENDING_OR_SKIPPED", "VERIFIED", "ADJUDICATED", "DOMAIN_VALIDATED", "RISK_VETO_CHECKED", "OUTPUT_OR_ACTION_PROPOSED", "OUTCOME_OBSERVED", "ATTRIBUTED", "REFLECTED", "LEARNING_CANDIDATES_CREATED", "CROSS_CONTEXT_VALIDATED", "UPDATED", "DEGRADED", "RETIRED", "ABSTAINED", "CANCELLED", "FAILED", "CLOSED")
TERMINAL = {"RETIRED", "ABSTAINED", "CANCELLED", "FAILED", "CLOSED"}
EXECUTION_STATES = set(STATES[8:24])
TRACE_STATES = set(STATES[9:24]) | {"CLOSED"}
FORWARD = {state: {STATES[index + 1]} for index, state in enumerate(STATES[:-1])}
FORWARD.update({"CONTEXT_RETRIEVED": {"CAPABILITY_GAP_MAPPED", "METHODS_DISCOVERED"}, "METHODS_SELECTED_OR_ABSTAINED": {"EVIDENCE_PLAN_READY", "CONTROL_TOWER_AUTHORIZED"}, "PRIMARY_RESULT_READY": {"CHALLENGE_PENDING_OR_SKIPPED", "VERIFIED", "ADJUDICATED"}, "ADJUDICATED": {"DOMAIN_VALIDATED", "RISK_VETO_CHECKED", "ABSTAINED"}, "DOMAIN_VALIDATED": {"RISK_VETO_CHECKED", "ABSTAINED"}, "RISK_VETO_CHECKED": {"OUTPUT_OR_ACTION_PROPOSED", "ABSTAINED"}, "OUTPUT_OR_ACTION_PROPOSED": {"OUTCOME_OBSERVED", "CLOSED"}, "CROSS_CONTEXT_VALIDATED": {"UPDATED", "DEGRADED", "RETIRED", "CLOSED"}})
for state in STATES:
    if state not in TERMINAL:
        FORWARD.setdefault(state, set()).update({"CANCELLED", "FAILED"})
REWORK = {"ADJUDICATED": {"EVIDENCE_PLAN_READY", "METHODS_DISCOVERED"}, "RISK_VETO_CHECKED": {"EVIDENCE_PLAN_READY", "METHODS_DISCOVERED", "EXECUTING"}, "DEGRADED": {"METHODS_DISCOVERED"}}


def _err(validator_id: str, code: str, path: str) -> ValidationError:
    return ValidationError(validator_id, code, path)


def validate_structure(record: dict[str, Any]) -> list[ValidationError]:
    version = record.get("schema_version")
    if version not in REQUIRED:
        return [_err("STRUCTURE", "SCHEMA_VERSION_UNSUPPORTED", "/schema_version")]
    errors = [_err("STRUCTURE", "REQUIRED_FIELD_MISSING", "/" + name) for name in REQUIRED[version] if name not in record or record[name] in (None, "")]
    for name in ("claim_ids", "handoff_refs", "unresolved_refs", "raw_trace_refs", "trace_refs"):
        if name in record and (not isinstance(record[name], list) or len(record[name]) != len(set(record[name]))):
            errors.append(_err("STRUCTURE", "ARRAY_UNIQUE_STRINGS_REQUIRED", "/" + name))
    if "retry_budget_remaining" in record and (not isinstance(record["retry_budget_remaining"], int) or record["retry_budget_remaining"] < 0):
        errors.append(_err("STRUCTURE", "NONNEGATIVE_INTEGER_REQUIRED", "/retry_budget_remaining"))
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
    elif v == "Mission/v1" and record.get("status") == "COMPLETED" and not (record.get("final_result_ref") or record.get("no_work_reason_ref")):
        errors.append(_err("M-COMPLETED-NEEDS-RESULT-OR-NO-WORK", "COMPLETION_REFERENCE_REQUIRED", "/status"))
    elif v == "Claim/v1":
        if record.get("claim_type") == "UNKNOWN" and record.get("confidence_class") != "UNKNOWN": errors.append(_err("C-UNKNOWN-CONFIDENCE-UNKNOWN", "UNKNOWN_CONFIDENCE_REQUIRED", "/confidence_class"))
        if record.get("claim_type") == "CAUSAL_HYPOTHESIS" and record.get("materiality") in {"HIGH", "CRITICAL"} and not record.get("falsifier_refs"): errors.append(_err("C-MATERIAL-CAUSAL-NEEDS-FALSIFIER", "FALSIFIER_REQUIRED", "/falsifier_refs"))
    elif v == "ChallengeCase/v1" and record.get("challenge_level") in {"C2", "C3", "C4"} and not record.get("independent_pass_ref"):
        errors.append(_err("CH-C2-C4-INDEPENDENT-PASS-REQUIRED", "INDEPENDENT_PASS_REQUIRED", "/independent_pass_ref"))
    elif v == "FormalHandoff/v1" and not record.get("raw_trace_refs"):
        errors.append(_err("FH-RAW-TRACE-REF-REQUIRED", "RAW_TRACE_REQUIRED", "/raw_trace_refs"))
    elif v == "OutcomeLearning/v1":
        if not (record.get("outcome_ref") or record.get("correction_event_ref") or record.get("audit_finding_ref")): errors.append(_err("OL-NEEDS-OUTCOME-CORRECTION-OR-AUDIT", "LEARNING_TRIGGER_REQUIRED", "/"))
        if record.get("requested_maturity") == "FORMAL_SKILL": errors.append(_err("OL-NO-DIRECT-FORMAL-SKILL", "FORMAL_SKILL_PROMOTION_FORBIDDEN", "/requested_maturity"))
    return errors


def validate_transition(current: str, target: str, rework: dict[str, Any] | None = None) -> list[ValidationError]:
    if target in FORWARD.get(current, set()): return []
    if target in REWORK.get(current, set()) and rework:
        errors = validate_structure(rework)
        if rework.get("retry_budget_remaining", 0) <= 0: errors.append(_err("RW-NO-RETRY-WHEN-BUDGET-ZERO", "REWORK_BUDGET_EXHAUSTED", "/retry_budget_remaining"))
        if not (rework.get("input_fingerprint_after") and rework["input_fingerprint_after"] != rework.get("input_fingerprint_before")) and not rework.get("escalation_ref"): errors.append(_err("RW-RETRY-REQUIRES-MATERIAL-CHANGE-OR-EXPLICIT-ESCALATION", "IDENTICAL_RETRY_FORBIDDEN", "/input_fingerprint_after"))
        return errors
    return [_err("DE-STATE-TRANSITION", "TRANSITION_FORBIDDEN", "/state")]


def validate_mission_graph(graph: dict[str, Any], *, authorization_refs: set[str]) -> list[ValidationError]:
    errors = validate_structure(graph)
    nodes = {node.get("work_item_id"): node for node in graph.get("nodes", []) if node.get("work_item_id")}
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    for edge in graph.get("edges", []):
        source, target = edge.get("from"), edge.get("to")
        if source not in nodes or target not in nodes: errors.append(_err("MG-ENDPOINT", "EDGE_ENDPOINT_UNKNOWN", "/edges")); continue
        if edge.get("type") in {"DEPENDS_ON", "BLOCKS"}: adjacency[source].add(target)
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
    return errors


def validate_organization(graph: dict[str, Any], *, alias_resolution: dict[str, list[str]], h2_authorized: bool = False) -> list[ValidationError]:
    errors: list[ValidationError] = []
    departments = {item.get("id"): item for item in graph.get("departments", []) if item.get("id")}
    owners: dict[str, list[str]] = {}
    for item in departments.values():
        domain = item.get("authority_domain")
        if domain and domain != "NONE": owners.setdefault(domain, []).append(item["id"])
        if item.get("node_kind") == "ROLE_TEMPLATE" and domain not in (None, "NONE"): errors.append(_err("OGV-032-ROLE-TEMPLATE-NONAUTHORITY", "ROLE_AUTHORITY_FORBIDDEN", "/departments"))
    if any(len(values) != 1 for values in owners.values()): errors.append(_err("OGV-001-UNIQUE-AUTHORITY", "AUTHORITY_NOT_UNIQUE", "/departments"))
    for edge in graph.get("edges", []):
        for key in ("from", "to"):
            endpoint = edge.get(key)
            if endpoint not in departments and endpoint != "USER" and endpoint not in alias_resolution: errors.append(_err("OGV-027-ROLE-AND-ALIAS-RESOLUTION", "EDGE_ENDPOINT_UNDECLARED", "/edges"))
    for alias, targets in alias_resolution.items():
        if len(targets) != 1 or targets[0] not in departments: errors.append(_err("OGV-027-ROLE-AND-ALIAS-RESOLUTION", "RETURN_ALIAS_NOT_UNIQUE", "/aliases/" + alias))
    if any(item.get("id") == "HARNESS_RUNTIME" and item.get("authority_domain") not in {"RUNTIME_ORCHESTRATION", "NONE"} for item in departments.values()): errors.append(_err("OGV-018-HARNESS-BOUNDARY", "HARNESS_TRUTH_AUTHORITY_FORBIDDEN", "/departments"))
    if h2_authorized: errors.append(_err("OGV-031-H1-H2-SLICE-SEPARATION", "H2_AUTHORIZATION_FORBIDDEN_IN_H1", "/h2_authorized"))
    return errors


def validate_trace_handoff(handoff: dict[str, Any], *, trace_ids: set[str], trace_level: str = "T1") -> list[ValidationError]:
    errors = validate_structure(handoff) + validate_semantics(handoff)
    if not set(handoff.get("raw_trace_refs", [])).issubset(trace_ids): errors.append(_err("OGV-011-TRACE-COMPLETENESS", "TRACE_INCOMPLETE", "/raw_trace_refs"))
    forbidden = {"raw_private_source_body", "credential_value", "access_token", "api_key", "private_key", "hidden_prompt", "private_chain_of_thought"}
    if forbidden.intersection(handoff): errors.append(_err("DE-NO-RAW-PRIVATE-BODY", "PRIVATE_TRACE_FIELD_FORBIDDEN", "/"))
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


def explore_critical_states() -> list[ValidationError]:
    """Bounded in-process exhaustive check of veto/retry/H1-H2 safety cases."""
    findings: list[ValidationError] = []
    for veto in ("PASS", "VETO"):
        for disposition in ("ACCEPTED", "ABSTAINED"):
            findings.extend(validate_semantics({"schema_version": "DecisionEpisode/v1", "decision_episode_id": "d", "mission_id": "m", "problem_signature_id": "p", "task_class": "OTHER", "materiality": "LOW", "risk_class": "R0", "state": "INTAKE", "created_at": "2026-01-01T00:00:00Z", "authority_snapshot_ref": "a", "trace_root_id": "t", "reproducibility_fingerprint": "f", "w7_veto_status": veto, "decision_status": disposition}))
    return findings


def validate_bundle(records: Iterable[dict[str, Any]]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for record in records:
        errors.extend(validate_structure(record)); errors.extend(validate_semantics(record))
    return errors
