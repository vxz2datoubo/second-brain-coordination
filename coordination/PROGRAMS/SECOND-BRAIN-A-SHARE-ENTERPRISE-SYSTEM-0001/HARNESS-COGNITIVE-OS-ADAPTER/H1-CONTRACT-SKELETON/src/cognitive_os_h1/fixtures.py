"""Public-safe synthetic fixture builders for H1 contract tests."""
from __future__ import annotations

from copy import deepcopy

from .contracts import REQUIRED_CANONICAL_NODES


NOW = "2026-08-15T00:00:00Z"


def canonical_organization() -> dict:
    """Small frozen baseline compiled from the canonical organization graph."""
    departments = []
    for node_id, (kind, authority) in REQUIRED_CANONICAL_NODES.items():
        node = {"id": node_id, "node_kind": kind, "authority_domain": authority}
        if node_id == "W7_VALIDATION_RISK":
            node["may_veto"] = ["FINAL_OUTPUT_OR_ACTION"]
        departments.append(node)
    return {
        "departments": departments,
        "dynamic_return_aliases": ["RESPONSIBLE_UPSTREAM"],
        "edges": [
            {"from": "SIGNAL_TOWER", "to": "CONTROL_TOWER_310"},
            {"from": "CONTROL_TOWER_310", "to": "HARNESS_RUNTIME"},
            {"from": "HARNESS_RUNTIME", "to": "PRIMARY_PRODUCER"},
            {"from": "PRIMARY_PRODUCER", "to": "CHALLENGER"},
            {"from": "CHALLENGER", "to": "W7_VALIDATION_RISK"},
            {"from": "W7_VALIDATION_RISK", "to": "W3_SECOND_BRAIN"},
            {"from": "W3_SECOND_BRAIN", "to": "RESPONSIBLE_UPSTREAM"},
        ],
    }


def episode(**extra: object) -> dict:
    record = {"schema_version": "DecisionEpisode/v1", "decision_episode_id": "de-1", "mission_id": "m-1", "problem_signature_id": "ps-1", "task_class": "ENGINEERING", "materiality": "LOW", "risk_class": "R1", "state": "INTAKE", "created_at": NOW, "authority_snapshot_ref": "auth-1", "trace_root_id": "trace-1", "reproducibility_fingerprint": "fp-1", "w7_veto_status": "PASS", "decision_status": "OPEN"}
    record.update(extra)
    return record


def handoff(**extra: object) -> dict:
    record = {"schema_version": "FormalHandoff/v1", "handoff_id": "h-1", "decision_episode_id": "de-1", "producer": "synthetic-producer", "consumer": "synthetic-consumer", "stage": "SYNTHETIC", "epistemic_status": "SUPPORTED", "input_fingerprint": "fp-1", "raw_trace_refs": ["trace-1"], "created_at": NOW}
    record.update(extra)
    return record


def copy_fixture(value: dict) -> dict:
    return deepcopy(value)
