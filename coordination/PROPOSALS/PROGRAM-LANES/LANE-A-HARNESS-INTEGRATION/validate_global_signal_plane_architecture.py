from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent

FILES = {
    "reconciliation": "UNIFIED-SIGNAL-TOWER-ARCHITECTURE-RECONCILIATION.yaml",
    "signal": "GLOBAL-SIGNAL-PLANE-CONTRACTS.yaml",
    "receipt": "GLOBAL-RECONCILIATION-RECEIPT-CONTRACT.yaml",
    "enterprise": "GLOBAL-SIGNAL-PLANE-ENTERPRISE-GOVERNANCE.yaml",
    "regression": "GLOBAL-SIGNAL-PLANE-REGRESSION-SPEC.yaml",
    "mission": "SIGNAL-TOWER-MISSION-ROUTER-CONTRACT.yaml",
    "intake": "GLOBAL-SIGNAL-INTAKE-ADAPTIVE-GATEWAY-CONTRACT.yaml",
    "runtime_receipt": "RUNTIME-INVOCATION-RECEIPT-CONTRACT.yaml",
    "dag": "IMPLEMENTATION-DEPENDENCY-DAG.yaml",
    "trace": "TRACE-LEDGER-PRIVACY-CONTRACT.yaml",
    "domain": "CROSS-PROJECT-DOMAIN-CONSUMER-BOUNDARY.yaml",
}

EXPECTED_IDS = {
    "reconciliation": ("reconciliation_id", "UNIFIED-SIGNAL-TOWER-ARCHITECTURE-RECONCILIATION-0001"),
    "signal": ("contract_id", "GLOBAL-SIGNAL-PLANE-CONTRACTS-0001"),
    "receipt": ("contract_id", "GLOBAL-RECONCILIATION-RECEIPT-CONTRACT-0001"),
    "enterprise": ("contract_id", "GLOBAL-SIGNAL-PLANE-ENTERPRISE-GOVERNANCE-0001"),
    "regression": ("spec_id", "GLOBAL-SIGNAL-PLANE-REGRESSION-SPEC-0001"),
    "mission": ("contract_id", "SIGNAL-TOWER-MISSION-ROUTER-CONTRACT-0001"),
    "intake": ("contract_id", "GLOBAL-SIGNAL-INTAKE-ADAPTIVE-GATEWAY-CONTRACT-0001"),
    "runtime_receipt": ("contract_id", "RUNTIME-INVOCATION-RECEIPT-CONTRACT-0001"),
    "dag": ("dag_id", "COGNITIVE-OS-HARNESS-IMPLEMENTATION-DEPENDENCY-DAG-0001"),
    "trace": ("contract_id", "COGNITIVE-OS-TRACE-LEDGER-PRIVACY-CONTRACT-0001"),
    "domain": ("contract_id", "COGNITIVE-OS-CROSS-PROJECT-DOMAIN-CONSUMER-BOUNDARY-0001"),
}


def load(name: str) -> dict:
    path = ROOT / FILES[name]
    if not path.exists():
        raise AssertionError(f"MISSING_FILE:{path.name}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"NOT_MAPPING:{path.name}")
    return data


def require(condition: bool, code: str, detail: object | None = None) -> None:
    if not condition:
        suffix = "" if detail is None else f":{json.dumps(detail, ensure_ascii=False, sort_keys=True)}"
        raise AssertionError(f"{code}{suffix}")


def main() -> int:
    docs = {name: load(name) for name in FILES}

    for name, (field, expected) in EXPECTED_IDS.items():
        require(docs[name].get(field) == expected, "IDENTITY_MISMATCH", {"file": FILES[name], "expected": expected})

    mission = docs["mission"]
    plane = mission.get("plane_boundary") or {}
    require(plane.get("unified_identity") == "ONE_SIGNAL_TOWER", "ONE_TOWER_IDENTITY_MISSING")
    required_pre = {
        "GLOBAL-SIGNAL-PLANE-CONTRACTS-0001",
        "GLOBAL-RECONCILIATION-RECEIPT-CONTRACT-0001",
        "GLOBAL-SIGNAL-PLANE-ENTERPRISE-GOVERNANCE-0001",
        "GLOBAL-SIGNAL-PLANE-REGRESSION-SPEC-0001",
    }
    require(required_pre <= set(plane.get("pre_mission_contracts") or []), "PRE_MISSION_CONTRACT_BINDING_INCOMPLETE")
    require(plane.get("no_second_signal_tower") is True, "SECOND_SIGNAL_TOWER_NOT_FORBIDDEN")
    require(plane.get("no_second_mission_router") is True, "SECOND_MISSION_ROUTER_NOT_FORBIDDEN")

    signal = docs["signal"]
    reliability = signal.get("reliability_model") or {}
    require(str(reliability.get("ingestion_delivery", "")).startswith("AT_LEAST_ONCE"), "INGESTION_DELIVERY_MODEL_INVALID")
    require("IDEMPOTENCY" in str(reliability.get("effective_processing", "")), "IDEMPOTENCY_MODEL_MISSING")
    require(reliability.get("event_history") == "APPEND_ONLY", "APPEND_ONLY_HISTORY_REQUIRED")
    require(reliability.get("projection") == "DERIVED / REBUILDABLE", "REBUILDABLE_PROJECTION_REQUIRED")
    require((signal.get("SignalCluster_v1") or {}).get("semantics", {}).get("cluster_may_authorize_execution") is False,
            "SIGNAL_CLUSTER_EXECUTION_AUTHORITY_LEAK")

    receipt = docs["receipt"]
    hard = receipt.get("hard_invariant") or {}
    require("NO_VALID_GLOBAL_RECONCILIATION_RECEIPT" in str(hard.get("rule", "")), "GLOBAL_RECEIPT_HARD_GATE_MISSING")
    require((receipt.get("freshness_binding") or {}).get("time_ttl_alone_is_sufficient") is False,
            "TIME_ONLY_RECEIPT_FRESHNESS_FORBIDDEN")
    require((receipt.get("freshness_binding") or {}).get("compare_and_check_required_at_release") is True,
            "RELEASE_COMPARE_AND_CHECK_REQUIRED")
    require("WorkClaim" in set(hard.get("not_equivalent_to") or []), "RECEIPT_AUTHORITY_SEPARATION_MISSING")

    enterprise = docs["enterprise"]
    principles = set(enterprise.get("enterprise_principles") or [])
    require("no single SUCCESS string as completion evidence" in principles, "SUCCESS_STRING_ANTI_PATTERN_MISSING")
    require((enterprise.get("observability") or {}).get("reuse_trace_ledger") is True, "TRACE_LEDGER_REUSE_REQUIRED")
    require((enterprise.get("security_and_privacy") or {}).get("cross_project_write_default") == "DENY",
            "CROSS_PROJECT_WRITE_MUST_DEFAULT_DENY")

    regression = docs["regression"]
    scenarios = regression.get("scenarios") or []
    ids = {item.get("id") for item in scenarios if isinstance(item, dict)}
    required_regressions = {
        "GST-R001-CROSS-WINDOW-STATE-DRIFT-R133",
        "GST-R002-STALE-REVIEW-HEAD",
        "GST-R003-RECEIPT-INVALIDATED-BY-MERGE",
        "GST-R004-SAME-AGENT-CROSS-PROJECT-DOUBLE-BOOK",
        "GST-R005-DUPLICATE-DELIVERY-SAME-CONTENT",
        "GST-R016-PROJECTION-REPLAY-EQUIVALENCE",
        "GST-R018-CRASH-AFTER-APPEND-BEFORE-PROJECTION",
        "GST-R024-CROSS-DOMAIN-NEGATIVE-TRANSFER",
    }
    require(required_regressions <= ids, "ENTERPRISE_REGRESSION_SET_INCOMPLETE", sorted(required_regressions - ids))

    intake = docs["intake"]
    authority = intake.get("authority_invariants") or {}
    require(authority.get("signal_tower_identity") == "ONE_SIGNAL_TOWER", "R136_ONE_TOWER_IDENTITY_MISSING")
    require(authority.get("no_second_signal_truth") is True, "R136_SECOND_SIGNAL_TRUTH_NOT_FORBIDDEN")
    require(authority.get("execution_authority") == "CONTROL_TOWER_310", "R136_EXECUTION_AUTHORITY_LEAK")
    require(authority.get("system_awareness_projection_is_not_authority") is True,
            "R136_SYSTEM_AWARENESS_AUTHORITY_LEAK")
    axes = intake.get("classification_axes") or {}
    require(set((axes.get("persistence") or {}).get("values") or []) == {"EPHEMERAL", "TRACE_ONLY", "DURABLE_SIGNAL"},
            "R136_PERSISTENCE_AXIS_INVALID")
    require(set((axes.get("execution") or {}).get("values") or []) == {"DIRECT", "DOMAIN_WORKFLOW", "GOVERNED_MISSION"},
            "R136_EXECUTION_AXIS_INVALID")
    require(set((axes.get("materiality") or {}).get("values") or []) == {"LOW", "MATERIAL", "HIGH_RISK"},
            "R136_MATERIALITY_AXIS_INVALID")
    require(axes.get("no_magic_score") is True, "R136_MAGIC_SCORE_FORBIDDEN")
    preflight = intake.get("GlobalSignalPreflight_v1") or {}
    require("NO_FRESH_VALID_GLOBAL_RECONCILIATION_RECEIPT" in str(preflight.get("hard_rule", "")),
            "R136_PRETASK_RECONCILIATION_GATE_MISSING")
    closure = intake.get("SignalClosureAssessment_v1") or {}
    closure_rules = closure.get("rules") or {}
    require(closure_rules.get("task_done_does_not_imply_signal_satisfied") is True,
            "R136_TASK_DONE_SIGNAL_SATISFACTION_CONFLATED")
    require(closure_rules.get("append_only_history_retained") is True,
            "R136_SIGNAL_CLOSURE_HISTORY_LOSS")

    runtime_receipt = docs["runtime_receipt"]
    rp = runtime_receipt.get("principles") or {}
    require(rp.get("self_declared_read_is_non_evidence") is True, "R136_SELF_CERTIFICATION_NOT_FORBIDDEN")
    require(rp.get("process_compliance_is_independent_from_outcome_quality") is True,
            "R136_PROCESS_OUTCOME_CONFLATED")
    require(rp.get("no_second_raw_trace_store") is True, "R136_SECOND_RAW_TRACE_STORE_NOT_FORBIDDEN")
    actual = runtime_receipt.get("actual_read_evidence") or {}
    require(actual.get("missing_evidence_disposition") == "UNVERIFIED", "R136_MISSING_EVIDENCE_MUST_BE_UNVERIFIED")
    film_profile = runtime_receipt.get("AI_FILM_DIRECTING_PROFILE_v1") or {}
    require(film_profile.get("canonical_entry") == "PROJECT_INDEX.yaml", "R136_AI_FILM_ENTRYPOINT_MISSING")
    require((film_profile.get("smoke_boundary") or {}).get("domain_mutation") == "FORBIDDEN_IN_R136",
            "R136_AI_FILM_WRITE_BOUNDARY_MISSING")
    require((film_profile.get("smoke_boundary") or {}).get("durable_signal_creation_for_routine_directing") is False,
            "R136_ROUTINE_DIRECTING_BACKLOG_POLLUTION")

    dag = docs["dag"]
    nodes = dag.get("nodes") or {}
    for node in ("S0A", "S0B", "S0C", "S0D", "S0E0", "H7A"):
        require(node in nodes, "DAG_NODE_MISSING", node)
    require(str(nodes["S0C"].get("state", "")).startswith("COMPLETED_CLOSED_R134"), "S0C_PROGRESS_NOT_RECONCILED")
    require(str(nodes["S0D"].get("state", "")).startswith("COMPLETED_CLOSED_R135"), "S0D_PROGRESS_NOT_RECONCILED")
    r136_lifecycle_states = {
        "PHASE_A_RESERVED_NON_EXECUTABLE",
        "PHASE_B_ACTIVE_IMPLEMENTATION",
        "COMPLETED_CLOSED_R136",
    }
    require(nodes["S0E0"].get("state") in r136_lifecycle_states, "R136_DAG_PHASE_INVALID")
    require("S0D" in set((nodes["S0E0"].get("requires") or [])), "R136_S0D_DEPENDENCY_MISSING")
    h7_requires = set((nodes["H7A"].get("requires") or []))
    require({"S0C", "S0E0", "H3C", "H4B"} <= h7_requires, "H7_DEPENDENCY_LOST")
    require((dag.get("principles") or {}).get("completed_node_does_not_authorize_successor") is True,
            "COMPLETED_NODE_AUTO_AUTHORIZATION_NOT_FORBIDDEN")
    s0c_locks = set(nodes["S0C"].get("locks") or [])
    require("no_Harness_runtime" in s0c_locks, "S0C_HARNESS_BOUNDARY_MISSING")
    require("no_private_chat_bridge" in s0c_locks, "S0C_PRIVATE_BOUNDARY_MISSING")
    require("NOT_AUTHORIZED" in str(nodes["H2A"].get("state", "")), "S0C_H2_BOUNDARY_MISSING")
    s0e_forbidden = set(nodes["S0E0"].get("forbidden") or [])
    require("DeepSeek_Harness_runtime" in s0e_forbidden, "R136_HARNESS_BOUNDARY_MISSING")
    require("private_chat_cross_window_bridge" in s0e_forbidden, "R136_PRIVATE_BRIDGE_BOUNDARY_MISSING")
    require("W3_runtime_mutation" in s0e_forbidden, "R136_W3_BOUNDARY_MISSING")
    require("AI_Film_or_domain_canonical_write" in s0e_forbidden, "R136_DOMAIN_WRITE_BOUNDARY_MISSING")

    reconciliation = docs["reconciliation"]
    require((reconciliation.get("architecture_verdict") or {}).get("result") ==
            "ACCEPT_HANDOFF_WITH_ARCHITECTURAL_REASSIGNMENT", "RECONCILIATION_VERDICT_MISSING")
    require((reconciliation.get("ai_film_domain_backlog_preservation") or {}).get("status") ==
            "AI_FILM_DOMAIN_BACKLOG_BOOTSTRAP_REQUIRED", "AI_FILM_BACKLOG_PRESERVATION_MISSING")

    trace = docs["trace"]
    principles_trace = trace.get("principles") or {}
    require(principles_trace.get("raw_once_reference_everywhere") is True, "RAW_ONCE_REFERENCE_EVERYWHERE_LOST")

    domain = docs["domain"]
    invariants = domain.get("current_invariants") or {}
    require(invariants.get("no_second_global_w3_in_ai_film") is True, "AI_FILM_SECOND_W3_NOT_FORBIDDEN")
    require(invariants.get("no_second_global_control_tower_in_ai_film") is True,
            "AI_FILM_SECOND_CONTROL_TOWER_NOT_FORBIDDEN")

    print(json.dumps({
        "result": "PASS",
        "validated_files": sorted(FILES.values()),
        "scenario_count": len(scenarios),
        "dag_signal_nodes": ["S0A", "S0B", "S0C", "S0D", "S0E0", "H7A"],
        "one_signal_tower": True,
        "r136_phase": nodes["S0E0"].get("state"),
        "runtime_self_certification_allowed": False,
        "harness_runtime_authorized": False,
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        raise SystemExit(2)
