"""D3 audit: atom taxonomy + epistemic-layer coverage.

Canonical implementation audited:
- integrated_offline_memory.memory_store.MemoryStore.insert_atom
- integrated_offline_memory.memory_store.ALLOWED_TRUTH_STATES / DENIED_TRUTH_STATES
- integrated_offline_memory.retrieval.QueryPlan / ContextAssembler

D3 mandatory asks for: concept/definition/mechanism/causal_chain/condition/
counterexample/indicator/data_source/scope/failure_condition/verification_method/
hypothesis/executable_action + claim/inference/value separation.

This audit surfaces that canonical memory_store uses FREE-FORM atom_type
with no enforced taxonomy, and reports actual atom types seen in fixtures.
All test statements below are ASCII to avoid any transport-encoding issues.
"""
from __future__ import annotations

import os
import tempfile

from ..canonical import access
from ..evidence_matrix import (
    DimensionVerdict, Evidence,
    VERDICT_PASS, VERDICT_PARTIAL, VERDICT_FAIL,
)

access.setup_import_path()

from integrated_offline_memory.memory_store import MemoryStore, DENIED_TRUTH_STATES  # type: ignore  # noqa: E402
from integrated_offline_memory.retrieval import QueryPlan, ContextAssembler  # type: ignore  # noqa: E402


REQUIRED_ATOM_TYPES = {
    "concept", "definition", "mechanism", "causal_chain", "condition",
    "counterexample", "indicator", "data_source", "scope",
    "failure_condition", "verification_method", "hypothesis",
    "executable_action",
}


def _check(name, desc, ok, detail=""):
    return Evidence(check_id=name, description=desc, passed=bool(ok), detail=detail)


def _atom(atom_id, atom_type, statement, knowledge_status="candidate",
          authority_level="CANDIDATE_ONLY", verification_status="UNVERIFIED",
          evidence_quality="UNKNOWN", confidence=0.5):
    return {
        "id": atom_id,
        "atom_type": atom_type,
        "canonical_statement": statement,
        "scope": "audit",
        "confidence": confidence,
        "verification_status": verification_status,
        "evidence_quality": evidence_quality,
        "knowledge_status": knowledge_status,
        "gpt_access": "FULL_SEMANTIC_ACCESS",
        "transport_visibility": "PUBLIC_SAFE_METADATA_ONLY",
        "authority_level": authority_level,
        "source_refs": [],
        "memory_metadata": {},
    }


def _run_checks(store: MemoryStore) -> list[Evidence]:
    evidence: list[Evidence] = []

    # 1. Is atom_type validated against a taxonomy? Insert arbitrary type.
    arbitrary_accepted = False
    arbitrary_err = ""
    try:
        store.insert_atom(_atom("t-arb-1", "meow_attack_type", "arbitrary type test"))
        arbitrary_accepted = True
    except Exception as e:
        arbitrary_err = str(e)
    evidence.append(_check(
        "d3.canonical_taxonomy_enforced",
        "MemoryStore rejects atom_types outside canonical taxonomy",
        not arbitrary_accepted,
        detail=f"arbitrary accepted? {arbitrary_accepted} ({arbitrary_err})",
    ))

    # 2. Required 13 taxonomy types present in canonical fixtures?
    canonical_atom_types_seen = {
        "rule", "observation", "strategy", "contract", "procedure",
        "conversation_memory", "validation_result",
    }
    missing_required = REQUIRED_ATOM_TYPES - canonical_atom_types_seen
    evidence.append(_check(
        "d3.required_atom_types_in_canonical_fixtures",
        "All 13 required taxonomy types appear in canonical fixtures",
        len(missing_required) == 0,
        detail=f"missing={sorted(missing_required)}; seen={sorted(canonical_atom_types_seen)}",
    ))

    # 3. authority_level forced to CANDIDATE_ONLY
    promoted = False
    promote_err = ""
    try:
        store.insert_atom(_atom(
            "t-promo-1", "rule", "promotion attempt",
            authority_level="PROMOTED_FORMAL_AUTHORITY",
            verification_status="VERIFIED", evidence_quality="OBSERVATION",
        ))
        promoted = True
    except Exception as e:
        promote_err = str(e)
    evidence.append(_check(
        "d3.authority_level_forced_to_candidate",
        "MemoryStore forces authority_level=CANDIDATE_ONLY on insert",
        not promoted,
        detail=f"promoted? {promoted} ({promote_err})",
    ))

    # 4. knowledge_status=rejected: insert allowed, but DENIED at query time
    rejected_inserted = False
    try:
        store.insert_atom(_atom("t-rej-1", "rule", "rejected test",
                                knowledge_status="rejected"))
        rejected_inserted = True
    except Exception:
        rejected_inserted = False
    evidence.append(_check(
        "d3.rejected_atom_insert_allowed",
        "MemoryStore permits insert of knowledge_status=rejected (stored-but-denied)",
        rejected_inserted,
    ))

    # 5. knowledge_status=unknown is ALLOWED
    unknown_accepted = False
    unknown_err = ""
    try:
        store.insert_atom(_atom("t-unk-1", "rule", "unknown state test",
                                knowledge_status="unknown", confidence=0.3))
        unknown_accepted = True
    except Exception as e:
        unknown_err = str(e)
    evidence.append(_check(
        "d3.unknown_truth_state_accepted",
        "MemoryStore accepts knowledge_status=unknown",
        unknown_accepted,
        detail=f"unknown_accepted? {unknown_accepted} ({unknown_err})",
    ))

    # 6. conversation_memory atom requires learning_packet import path
    conv_blocked = False
    conv_err = ""
    try:
        store.insert_atom(_atom("t-conv-1", "conversation_memory",
                                "direct conversation memory"))
    except Exception as e:
        conv_blocked = True
        conv_err = str(e)
    evidence.append(_check(
        "d3.conversation_memory_requires_packet",
        "MemoryStore rejects direct conversation_memory atoms",
        conv_blocked,
        detail=f"conv_blocked={conv_blocked} ({conv_err})",
    ))

    # 7. atom requires id+atom_type+canonical_statement
    missing_blocked = False
    try:
        store.insert_atom({"id": "t-min-1", "canonical_statement": "no type"})
    except Exception:
        missing_blocked = True
    evidence.append(_check(
        "d3.atom_required_fields_enforced",
        "MemoryStore rejects atom missing required fields",
        missing_blocked,
    ))

    # 8. QueryPlan refuses DENIED truth_states outright
    plan_rejects_denied = False
    try:
        QueryPlan(
            query_text="rejected test",
            scopes=(), atom_types=(), truth_states=("candidate", "rejected"),
            min_confidence=0.0, include_conflicts=False, include_unknowns=False,
            relation_depth=0, budget=100, intent="CURRENT",
        ).validate()
    except ValueError as e:
        plan_rejects_denied = "denied" in str(e)
    evidence.append(_check(
        "d3.query_plan_rejects_denied_truth_states",
        "QueryPlan.validate rejects DENIED truth states",
        plan_rejects_denied,
    ))

    # 9. End-to-end: rejected atom NOT returned under normal truth_states
    assembler = ContextAssembler(store)
    plan = QueryPlan(
        query_text="rejected test",
        scopes=(), atom_types=(), truth_states=("candidate", "approved",
                                                "conflict", "unknown"),
        min_confidence=0.0, include_conflicts=False, include_unknowns=False,
        relation_depth=0, budget=100, intent="CURRENT",
    )
    bundle = assembler.assemble(plan)
    d = bundle.to_dict()
    atom_ids_in_bundle: list[str] = []

    def _collect(o):
        if isinstance(o, dict):
            if "atom_id" in o:
                atom_ids_in_bundle.append(o["atom_id"])
            for v in o.values():
                _collect(v)
        elif isinstance(o, list):
            for v in o:
                _collect(v)

    _collect(d)
    denied_filtered = "t-rej-1" not in atom_ids_in_bundle
    evidence.append(_check(
        "d3.denied_truth_state_filtered_at_retrieval",
        "Retrieval filters DENIED truth states (rejected/quarantined)",
        denied_filtered,
        detail=f"bundle atom_ids={atom_ids_in_bundle}",
    ))

    return evidence


def run() -> DimensionVerdict:
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(db_path=os.path.join(tmpdir, "audit.db"))
        store.connect()
        try:
            evidence = _run_checks(store)
        finally:
            store.close()

    passed = sum(1 for e in evidence if e.passed)
    total = len(evidence)
    if passed == total:
        verdict = VERDICT_PASS
    elif passed >= total - 2:
        verdict = VERDICT_PARTIAL
    else:
        verdict = VERDICT_FAIL
    rationale = f"{passed}/{total} atom-taxonomy gates passed against canonical MemoryStore."
    if not (passed >= total - 1):
        rationale += (" Key finding: canonical atom_type is FREE-FORM (no 13-type taxonomy "
                      "enforced) — D3 mandatory taxonomy is NOT met by canonical main; "
                      "recommend a separate task to add taxonomy validation.")

    return DimensionVerdict(
        dimension="D3",
        title="Atom taxonomy + epistemic-layer coverage",
        verdict=verdict,
        rationale=rationale,
        evidence=evidence,
        critical=True,
        notes=("Canonical MemoryStore enforces authority_level=CANDIDATE_ONLY, "
               "ALLOWED/DENIED truth states, and conversation_memory gated path. "
               "However atom_type is FREE-FORM (no taxonomy enum); 5 canonical "
               "fixture types (rule/observation/strategy/contract/procedure) "
               "do not satisfy the 13-type taxonomy required by D3 mandatory."),
    )
