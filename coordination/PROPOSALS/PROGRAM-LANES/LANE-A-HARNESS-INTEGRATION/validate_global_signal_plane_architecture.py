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

    dag = docs["dag"]
    nodes = dag.get("nodes") or {}
    for node in ("S0A", "S0B", "S0C", "S0D", "H7A"):
        require(node in nodes, "DAG_NODE_MISSING", node)
    require("S0C" in set((nodes["H7A"].get("requires") or [])), "H7_MUST_DEPEND_ON_S0C")
    require("H3C" in set((nodes["H7A"].get("requires") or [])), "H7_H3_DEPENDENCY_LOST")
    require("H4B" in set((nodes["H7A"].get("requires") or [])), "H7_H4_DEPENDENCY_LOST")
    forbidden = set(nodes["S0C"].get("forbidden") or [])
    require("DeepSeek_Harness_runtime" in forbidden, "S0C_HARNESS_BOUNDARY_MISSING")
    require("H2_auto_start" in forbidden, "S0C_H2_BOUNDARY_MISSING")

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
        "dag_signal_nodes": ["S0A", "S0B", "S0C", "S0D", "H7A"],
        "one_signal_tower": True,
        "harness_runtime_authorized": False,
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        raise SystemExit(2)
