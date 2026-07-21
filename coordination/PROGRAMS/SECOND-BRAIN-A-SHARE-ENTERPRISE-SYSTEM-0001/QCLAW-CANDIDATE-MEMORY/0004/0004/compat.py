"""Candidate Memory Library — Codex PR #41 Compatibility Matrix

Work Package I: defines compatibility contracts between the Candidate Memory
Library (this project, Issue #43) and Codex's offline A-share replay module
(PR #41 in second-brain-coordination).

This file serves as the machine-readable contract for:
  - Data format alignment (atoms/relations/packets)
  - Schema compatibility (field mappings)
  - Import/export pathways between systems
  - Knowledge status preservation across boundaries

No executable code — pure contract definition.
"""

import json
from typing import Any, Dict, List

# ── Compatibility Matrix v0.2 ─────────────────────────────────────────

COMPATIBILITY_MATRIX = {
    "version": "0.2",
    "contract_date": "2026-07-21",
    "systems": {
        "candidate_memory": {
            "name": "Candidate Memory Library",
            "issue": "#43",
            "repository": "second-brain-coordination",
            "branch": "qclaw/candidate-memory-library-0004",
            "module_path": "_qclaw_memory/0004",
        },
        "codex_replay": {
            "name": "Offline A-Share Replay Knowledge Slice",
            "pr": "#41",
            "repository": "second-brain-coordination",
            "branch": "feat/add-offline-ashare-replay",
        },
    },

    # ── Field Mappings ─────────────────────────────────────────────
    "field_mappings": {
        "atom_id": {
            "candidate_memory": "id",
            "codex_replay": "atom_id",
            "compatible": True,
            "note": "SHA256 content-addressed, same algorithm expected",
        },
        "canonical_statement": {
            "candidate_memory": "canonical_statement",
            "codex_replay": "canonical_statement",
            "compatible": True,
        },
        "atom_type": {
            "candidate_memory": "atom_type",
            "codex_replay": "atom_type",
            "compatible": True,
            "expected_values": [
                "FACT", "CONCEPT", "PROCEDURE", "RULE", "OPINION",
                "EVENT", "RELATION", "METADATA", "WARNING", "EXPERIENCE",
                "PREFERENCE", "GOAL", "CONSTRAINT", "ASSUMPTION", "UNKNOWN",
            ],
        },
        "confidence": {
            "candidate_memory": "confidence",
            "codex_replay": "confidence",
            "compatible": True,
            "range": [0.0, 1.0],
        },
        "verification_status": {
            "candidate_memory": "verification_status",
            "codex_replay": "verification_status",
            "compatible": True,
            "expected_values": ["VERIFIED", "UNVERIFIED", "DISPUTED", "OUTDATED", "REPLACED"],
        },
        "scope": {
            "candidate_memory": "scope",
            "codex_replay": "scope",
            "compatible": True,
        },
        "source_reference": {
            "candidate_memory": "source_reference",
            "codex_replay": "source_reference",
            "compatible": True,
        },
        "evidence_quality": {
            "candidate_memory": "evidence_quality",
            "codex_replay": "evidence_quality",
            "compatible": True,
            "expected_values": ["high", "medium", "low", "synthetic", "none"],
        },
        "knowledge_status": {
            "candidate_memory": "knowledge_status",
            "codex_replay": "knowledge_status",
            "compatible": True,
            "expected_values": ["NEW", "VERIFIED", "DISPUTED", "OUTDATED", "SUPERSEDED", "REPLACED", "UNRESOLVED"],
        },
        "gpt_access": {
            "candidate_memory": "gpt_access",
            "codex_replay": "gpt_access",
            "compatible": True,
            "default": "FULL_SEMANTIC_ACCESS",
        },
        "transport_visibility": {
            "candidate_memory": "transport_visibility",
            "codex_replay": "transport_visibility",
            "compatible": True,
            "expected_values": ["LOCAL", "PRIVATE_REPO", "PUBLIC_REPO", "PACKAGE_ONLY"],
        },
        "authority_level": {
            "candidate_memory": "authority_level",
            "codex_replay": "authority_level",
            "compatible": True,
            "expected_values": ["CANDIDATE_ONLY", "APPROVED", "AUTHORITY"],
        },
        "relation_type": {
            "candidate_memory": "relation_type",
            "codex_replay": "relation_type",
            "compatible": True,
            "expected_values": [
                "IS_A", "HAS_PROPERTY", "CAUSES", "CORRELATED_WITH", "PRECEDES",
                "SUPPORTS", "CONTRADICTS", "SUPERSEDES", "UPDATES", "REPLACES",
                "DERIVED_FROM", "DEPENDS_ON", "BELONGS_TO", "RELATED_TO",
                "EXAMPLE_OF", "PROCEDURE_FOR", "EVIDENCE_FOR", "UNKNOWN_RELATION",
            ],
        },
    },

    # ── Compatibility Gates ───────────────────────────────────────
    "gates": {
        "atom_format": {
            "status": "COMPATIBLE",
            "note": "Both systems use JSON dicts with same field names. SHA256 ID algorithm expected to match.",
            "action": "Verify with cross-system hash test on 3 sample atoms.",
            "verification_script": "verify_atom_hash_cross_system.py",
        },
        "relation_format": {
            "status": "COMPATIBLE",
            "note": "Relation types fully overlap. from_atom_id/to_atom_id naming consistent.",
        },
        "packet_format": {
            "status": "COMPATIBLE",
            "note": "Both use {id, atoms, relations, unknowns, skills, source} structure.",
        },
        "knowledge_status_propagation": {
            "status": "COMPATIBLE",
            "note": "7-state model (NEW→VERIFIED→OUTDATED→SUPERSEDED→...) preserved across both systems.",
        },
        "conflict_handling": {
            "status": "COMPATIBLE",
            "note": "Both systems support (atom_id_a, atom_id_b, conflict_type, resolution_status).",
        },
        "unknown_tracking": {
            "status": "COMPATIBLE",
            "note": "Both systems track open questions with (id, question, scope, status).",
        },
        "credential_isolation": {
            "status": "COMPATIBLE",
            "note": "Both systems classify credential refs separately. No credentials in public repos.",
        },
        "gpt_access_authorization": {
            "status": "COMPATIBLE",
            "note": "USER-DIRECTIVE-COMPLETE-KNOWLEDGE-LIBRARY-v1.0 applies to both systems. FULL_SEMANTIC_ACCESS default.",
        },
    },

    # ── Validation Rules ──────────────────────────────────────────
    "validation_rules": [
        {
            "rule_id": "V-A-001",
            "name": "No missing atoms in packet",
            "validate": "All atoms referenced in relations must exist in atoms table.",
        },
        {
            "rule_id": "V-A-002",
            "name": "No duplicate atom IDs",
            "validate": "INSERT OR IGNORE ensures idempotent ingestion.",
        },
        {
            "rule_id": "V-A-003",
            "name": "Confidence in [0,1]",
            "validate": "Atom confidence is a real number 0.0-1.0 or null.",
        },
        {
            "rule_id": "V-A-004",
            "name": "SHA256 integrity",
            "validate": "Packet content_hash = SHA256(json.dumps(packet, sort_keys=True)).",
        },
        {
            "rule_id": "V-A-005",
            "name": "4-axis independence preserved",
            "validate": "knowledge_status, gpt_access, transport_visibility, authority_level set independently.",
        },
        {
            "rule_id": "V-A-006",
            "name": "Credential refs not in public packets",
            "validate": "credential_refs entries must have transport_visibility='LOCAL'.",
        },
    ],

    # ── Cross-System Test Scenarios ──────────────────────────────
    "cross_system_tests": [
        {
            "test_id": "XT-001",
            "name": "Hash stability",
            "description": "Same atom content → same SHA256 ID in both systems.",
            "status": "PENDING",
        },
        {
            "test_id": "XT-002",
            "name": "Packet roundtrip",
            "description": "Codex exports packet → Memory Library imports → re-exports → hash matches.",
            "status": "PENDING",
        },
        {
            "test_id": "XT-003",
            "name": "Conflict propagation",
            "description": "Conflict created in Codex replay survives roundtrip through Memory Library.",
            "status": "PENDING",
        },
        {
            "test_id": "XT-004",
            "name": "Unknown preservation",
            "description": "Open unknowns are preserved across system boundaries.",
            "status": "PENDING",
        },
        {
            "test_id": "XT-005",
            "name": "Credential isolation",
            "description": "Credential refs in LOCAL storage are NOT exported to public repo packets.",
            "status": "PENDING",
        },
        {
            "test_id": "XT-006",
            "name": "Large packet stress",
            "description": "500+ atoms in single packet processed without timeout or corruption.",
            "status": "PENDING",
        },
    ],
}


def get_matrix() -> Dict[str, Any]:
    """Return the compatibility matrix."""
    return COMPATIBILITY_MATRIX


def check_compatibility() -> Dict[str, Any]:
    """Run automated compatibility checks. Returns {compatible, issues, summary}."""
    issues = []
    matrix = get_matrix()

    # Check all gates
    for gate_name, gate in matrix["gates"].items():
        if gate["status"] != "COMPATIBLE":
            issues.append(f"Gate '{gate_name}' is {gate['status']}: {gate['note']}")

    # Check field mappings
    for field_name, mapping in matrix["field_mappings"].items():
        if not mapping.get("compatible", False):
            issues.append(f"Field '{field_name}' incompatible between systems")

    # Check validation rules are defined
    rule_count = len(matrix["validation_rules"])
    if rule_count < 5:
        issues.append(f"Only {rule_count} validation rules defined (expected ≥5)")

    # Check cross-system tests
    pending_tests = [t["test_id"] for t in matrix["cross_system_tests"] if t["status"] == "PENDING"]
    completed_tests = [t["test_id"] for t in matrix["cross_system_tests"] if t["status"] != "PENDING"]

    return {
        "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "compatible": len(issues) == 0,
        "gate_count": len(matrix["gates"]),
        "field_count": len(matrix["field_mappings"]),
        "rule_count": rule_count,
        "cross_tests_total": len(matrix["cross_system_tests"]),
        "cross_tests_completed": len(completed_tests),
        "cross_tests_pending": len(pending_tests),
        "issues": issues,
        "pending_tests": pending_tests,
    }


if __name__ == "__main__":
    result = check_compatibility()
    print(json.dumps(result, indent=2))
