"""R60 benchmark case contract (schema) and canonical contract source registry.

QCLAW is the P2 batch evaluation factory only. Every case must trace its
expected outcome to an accepted canonical contract. This module is the single
source of truth for (a) the required case fields and (b) the frozen canonical
contract file identity (repo-relative path + git blob SHA) that each case's
`canonical_contract_source` must reference.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# ── required case fields (per R60 route `case_contract.required_fields`) ────
REQUIRED_CASE_FIELDS: tuple[str, ...] = (
    "case_id",
    "canonical_contract_source",
    "setup",
    "query_and_intent",
    "expected_admission_or_abstention",
    "forbidden_outcome",
    "failure_significance",
    "applicable_slice",
)

# ── the accepted canonical contracts this benchmark traces against ─────────
# Each entry: repo-relative path -> git blob SHA at the audited origin/main head
# (33b3e0fa310ccb72b32c99f125bdacc6cb894892). Expected outcomes are derived
# ONLY from these files; anything not frozen here is UNKNOWN / escalated.
CANONICAL_CONTRACTS: dict[str, str] = {
    # Phase-3 runtime contracts (currently the only runnable reference)
    "PHASE-3/src/integrated_offline_memory/retrieval.py": "40a3b50f93250db207bf20a1bbe454bd98ab1559",
    "PHASE-3/src/integrated_offline_memory/memory_store.py": "e13b2e8fc926a61448c7717e954e4dde245517eb",
    "PHASE-3/src/integrated_offline_memory/conversation_memory.py": "124e2de776e5d2b451613cd7afa168fcf7df7b5b",
    "PHASE-3/src/integrated_offline_memory/learning_packet.py": "4d900bdc47c3358ec10e9df260422b44755d98db",
    "PHASE-3/src/integrated_offline_memory/canonical.py": "344b929c44c413bce55838ba1fcbae2b1e31beb5",
    # Accepted P2 plan + P2.1 route (spec contracts for not-yet-runtime slices)
    "R116-P2/P2-UNIFIED-RETRIEVAL-AND-CONTEXT-BUNDLE-IMPLEMENTATION-PLAN.md": "fc4193baa6cf33cea4a4426ea06022c82e8108ff",
    "ROUTES/CODEX-R117-P2-1-UNIFIED-CANDIDATE-ADMISSION.yaml": "4257b3f69d1976a9f01315eaf8cffd0846eaab60",
    "ROUTES/QCLAW-R60.yaml": "942092749145b3cda1806d6e589a5a4e89fb91d1",
}

# Full repo-relative paths (for the harness to verify blob SHA against the tree)
CANONICAL_CONTRACT_PATHS: dict[str, str] = {
    "PHASE-3/src/integrated_offline_memory/retrieval.py": (
        "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
        "PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/retrieval.py"
    ),
    "PHASE-3/src/integrated_offline_memory/memory_store.py": (
        "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
        "PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/memory_store.py"
    ),
    "PHASE-3/src/integrated_offline_memory/conversation_memory.py": (
        "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
        "PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/conversation_memory.py"
    ),
    "PHASE-3/src/integrated_offline_memory/learning_packet.py": (
        "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
        "PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/learning_packet.py"
    ),
    "PHASE-3/src/integrated_offline_memory/canonical.py": (
        "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
        "PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/canonical.py"
    ),
    "R116-P2/P2-UNIFIED-RETRIEVAL-AND-CONTEXT-BUNDLE-IMPLEMENTATION-PLAN.md": (
        "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
        "CODEX-GPT-SECOND-BRAIN-R116-P2/P2-UNIFIED-RETRIEVAL-AND-CONTEXT-BUNDLE-IMPLEMENTATION-PLAN.md"
    ),
    "ROUTES/CODEX-R117-P2-1-UNIFIED-CANDIDATE-ADMISSION.yaml": (
        "coordination/ROUTES/CODEX-GPT-SECOND-BRAIN-COGNITIVE-CLOSED-LOOP-FUSION-R117-P2-1-UNIFIED-CANDIDATE-ADMISSION.yaml"
    ),
    "ROUTES/QCLAW-R60.yaml": (
        "coordination/ROUTES/QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60.yaml"
    ),
}

# 11 required dimensions (from R60 route `benchmark_scope.required_dimensions`)
DIMENSIONS: tuple[str, ...] = (
    "scope_isolation_cross_domain_denial",
    "current_historical_valid_at",
    "stale_revoked_superseded_no_resurrection",
    "channel_admission_parity",
    "hidden_disallowed_relation_conflict_endpoint",
    "synthetic_aggregate_no_double_vote",
    "support_and_counter_alternative_coverage",
    "material_unknown_and_no_evidence_abstain",
    "provenance_redaction_no_raw_pointer_body",
    "deterministic_ordering_dedup_budget",
    "prompt_injection_secret_fail_closed",
)

# P2 slices (from R116 plan `Authorized implementation slices`)
SLICES: tuple[str, ...] = ("P2.1", "P2.2", "P2.3", "P2.4")

# Epistemic status for an expected outcome
EXPECTED_VERDICT_KINDS: tuple[str, ...] = (
    "ADMIT",        # must be admitted into the bundle
    "ABSTAIN",      # trust gate must ABSTAIN
    "REJECT",       # must be rejected by admission (never in bundle)
    "UNKNOWN",      # contract ambiguous -> escalate to GPT, not gradable
)


def git_blob_sha(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\x00"
    return hashlib.sha1(header + data).hexdigest()


def validate_case(case: dict) -> list[str]:
    """Return list of structural errors for a single case (empty == valid)."""
    errors: list[str] = []
    missing = [f for f in REQUIRED_CASE_FIELDS if f not in case or case[f] in (None, "")]
    if missing:
        errors.append("missing_fields:" + ",".join(missing))
    if "case_id" in case and (not isinstance(case["case_id"], str) or not case["case_id"].strip()):
        errors.append("case_id_invalid")
    src = case.get("canonical_contract_source")
    if src is not None and src not in CANONICAL_CONTRACTS:
        errors.append("canonical_contract_source_unknown:" + str(src))
    slice_ = case.get("applicable_slice")
    if slice_ is not None and slice_ not in SLICES:
        errors.append("applicable_slice_invalid:" + str(slice_))
    exp = case.get("expected_admission_or_abstention")
    if exp is not None and not isinstance(exp, dict):
        errors.append("expected_admission_or_abstention_must_be_object")
    elif exp is not None:
        if exp.get("verdict") not in EXPECTED_VERDICT_KINDS:
            errors.append("expected_verdict_invalid:" + str(exp.get("verdict")))
    return errors


def dump_json(value: dict | list) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
